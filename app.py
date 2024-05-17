from flask import Flask, request, jsonify
import json
import requests
import os
import re
from bs4 import BeautifulSoup
from openai import OpenAI

app = Flask(__name__)

MODEL = "gpt-4o"

response_format_1 = """
Hi [Customer's Name],

Thank you for reaching out to us regarding the issue with logging into your account. I understand this must be frustrating, and I apologize for any inconvenience caused.

Based on your description, it sounds like this could be related to [a brief description of the suspected issue, e.g., a recent system update, credentials problem, etc.]. To address this efficiently, I have a couple of questions:

Have you recently updated any login details or account settings?
Are there any specific error messages when you attempt to log in? If yes, could you please provide a screenshot?
In the meantime, here are a few steps that often help resolve similar issues:

Update your browser to the latest version.
Clear your browser's cache and cookies.
Try accessing your account using a different browser or device.
Please try these steps and let me know the outcome. If they solve the problem, you can click the "Resolve" button to close this ticket. If the issue persists, please reply to this message with your answers to the above questions, and we will continue to assist you.

Looking forward to your response.

Best regards,

Service Desk AI Agent
"""

response_format_2 = """
Hi [Customer's Name],

Thank you for reaching out to us regarding your need to update your profile information. I'm here to help!

<explanation of what the customer is requesting>

If you encounter any issues or have further questions, please do not hesitate to contact us again. We are always here to assist you!

Looking forward to your response.

Best regards,

Service Desk AI Agent
"""

def clean_text(text):
    cleaned_text = re.sub(r'\n+', '\n', text)
    return cleaned_text

def convert_to_adf(text):
    # Split the text into paragraphs based on double newlines
    paragraphs = text.split('\n\n')
    
    # Initialize the content structure for ADF
    adf_content = {
        "body": {
            "content": [],
            "type": "doc",
            "version": 1
        }
    }

    for paragraph in paragraphs:
        # Create a list to hold the content of the current paragraph
        paragraph_content = []

        # Split the paragraph into parts based on bold markers (**)
        parts = re.split(r'(\*\*.*?\*\*)', paragraph)

        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                # It's a bold part, remove the markers and format as bold
                bold_text = part[2:-2]
                paragraph_content.append({
                    "type": "text",
                    "text": bold_text,
                    "marks": [
                        {
                            "type": "strong"
                        }
                    ]
                })
            else:
                # It's a normal text part
                paragraph_content.append({
                    "type": "text",
                    "text": part
                })

        # Add the current paragraph to the ADF content
        adf_content["body"]["content"].append({
            "type": "paragraph",
            "content": paragraph_content
        })

    # Convert the ADF content to a JSON string
    adf_json = json.dumps(adf_content, indent=2)
    return adf_json

def fetch_articles(summary, HEADERS_EXP, BASE_URL):
    url = f"{BASE_URL}/rest/servicedeskapi/knowledgebase/article?query={(summary)}&highlight=false"
    try:
        response = requests.get(url, headers=HEADERS_EXP)
        response.raise_for_status()
        articles = response.json()['values']
        return articles
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch articles from JSM: {e}")
        return []

def respond_to_customer(OPENAI_API_KEY, content, summary, description, reporter):
    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a service desk agent responsible for handling customer inquiries."},
                {"role": "user", "content": f"To answer the inquiry, you need to check the content I'll provide you which is from our knowledge base, keep in mind that the articles are in the order of what apparently the customer is asking:\n\n{content}.\n\nYour signature should always be 'Best regards,\nService Desk AI Agent\n\nThe response should be professional and cordial like these examples (you don't need to follow that exact same format):\n\n{response_format_1}\n\n{response_format_2}. \n\nIf you don't know the answer or didn't understand the question, just tell the customer that you are goinf to escalate the isso to one of our human agents."},
                {"role": "assistant", "content": "Sure, I'll look into this for you right away. Can you please provide the details of the ticket?"},
                {"role": "user", "content": f"Sure, the summary of the ticket is: {summary}.\n\nThe description is:\n\n{description}.\n\nThe ticket was reported by {reporter}."}
            ],
            temperature=0.2,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"ERROR: An error occurred: {e}")
        return ""

def post_comment(issue_id, comment, headers, BASE_URL):
    payload = ""
    url = f"{BASE_URL}/rest/servicedeskapi/request/{issue_id}/comment"
    payload = json.dumps({
        "body": comment,
        "public": True
    })
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        print("Comment posted successfully")
    except requests.exceptions.RequestException as e:
        print(f"Failed to post comment: {e}")

    return payload

@app.route('/process', methods=['POST'])
def process_event():
    event = request.get_json()
    summary = event['summary']
    description = event['description']
    reporter = event['reporter']
    BASE_URL = event['BASE_URL']
    issue_key = event['issue_key']
    
    AUTHORIZATION = request.headers.get('Authorization')
    OPENAI_API_KEY = request.headers.get('Openai-Api-Key')

    HEADERS_EXP = {
        'Accept': 'application/json',
        'X-ExperimentalApi': 'opt-in',
        'Content-Type': 'application/json',
        'Authorization': f"Basic {AUTHORIZATION}",
        'Connection': 'keep-alive',
        'Accept-Encoding': 'utf-8'
    }

    articles = fetch_articles(summary, HEADERS_EXP, BASE_URL)
    content = ""

    if articles:
        for article in articles:
            title = article['title']
            url = article['content']['iframeSrc']
            try:
                response = requests.get(url, headers=HEADERS_EXP)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, features="html.parser")
                for script in soup(["script", "style"]):
                    script.extract()
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                article = f"\n\n\nTitle: {title}\n\nContent:\n\n{clean_text(text)}"
                content += str(article)
            except requests.exceptions.HTTPError as e:
                print(f"ERROR: HTTP Error for URL {url}: {str(e)}")
            except Exception as e:
                print(f"ERROR: An error occurred while processing URL {url}: {str(e)}")

    response_content = respond_to_customer(OPENAI_API_KEY, content, summary, description, reporter)
    comment = post_comment(issue_key, response_content, HEADERS_EXP, BASE_URL)
    return comment

@app.route('/')
def index():
    return "Hello, this is your Flask app running on Heroku!"

if __name__ == "__main__":
    app.run(debug=True)
