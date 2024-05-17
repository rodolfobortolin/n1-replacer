
# Jira Service Management Automation Script

This repository contains a Flask application that automates responses to customer inquiries in Jira Service Management (JSM) using OpenAI's GPT-4o model. The script processes incoming requests, fetches relevant articles from the JSM knowledge base, and generates appropriate responses based on the customer's query.

## Features

- Fetches relevant articles from the JSM knowledge base.
- Generates AI-based responses to customer inquiries using OpenAI's GPT-4 model.
- Posts responses as comments on the respective Jira issues.

## Prerequisites

- Python 3.8 or higher
- Flask
- Requests
- BeautifulSoup4
- OpenAI

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/rodolfobortolin/n1-replacer.git
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Ensure you your automation rule is sending the following keys in the header:

- `Authorization`: Your OpenAI API key.
- `Openai-Api-Key`: The base URL for your Jira Service Management instance.

## Usage

1. Start the Flask application:
   ```bash
   python app.py
   ```

2. The application will be available at `http://localhost:5000`.

## API Endpoints

### Process Event

- **URL:** `/process`
- **Method:** `POST`
- **Description:** Processes incoming Automation rule trigger, generates a response using OpenAI, and posts the response as a comment on the Jira issue.
- **Request Headers:**
  - `Authorization`: Basic auth header with JSM credentials.
  - `Openai-Api-Key`: Your OpenAI API key.
- **Request Body:**
  ```json
  {
    "summary": "{{htmlEncode(issue.summary)}}",
    "description": "{{htmlEncode(issue.description)}}",
    "reporter": "{{issue.reporter.displayName}}",
    "BASE_URL": "{{baseUrl}}",
    "issue_key": "{{issue.key}}"
  }
  ```

## Example Response

```json
{
  "body": "Generated response from OpenAI",
  "public": true
}
```

## How It Works

1. The `/process` endpoint receives a POST request with details of the JSM event.
2. The `fetch_articles` function retrieves relevant knowledge base articles from JSM based on the issue summary.
3. The `respond_to_customer` function generates a response using OpenAI's GPT-4 model.
4. The `post_comment` function posts the generated response as a comment on the Jira issue.

## Additional Information

<URL of the blogpost>

---

### Author

Rodolfo Bortolin
rodolfobortolin@gmail.com
