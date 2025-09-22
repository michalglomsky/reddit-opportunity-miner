# ⛏️ Reddit Opportunity Miner 1.0

## 📄 Overview

Reddit Opportunity Miner is a Python-based command-line tool designed to analyze Reddit subreddits to identify potential business opportunities, user pain points, and ideas suitable for automation or AI-powered solutions.

It uses a hybrid data fetching strategy, leveraging the official Reddit API (via PRAW) for recent data and the Pushshift API for historical data. The core of the tool is an analysis pipeline orchestrated by LangGraph, which uses a Large Language Model (via Groq) to perform deep analysis and classification on relevant Reddit posts.

All findings are stored in a local SQLite database, allowing for persistent storage and sophisticated, time-based analysis of opportunities across multiple runs.

## ✨ Features

-   🔄 **Hybrid Data Fetching:** Uses PRAW for recent posts and Pushshift for historical archives.
-   🤖 **AI-Powered Analysis:** Leverages a Groq-powered LLM (`llama-3.3-70b-versatile`) to analyze post content and comments.
-   💡 **Structured Insights:** Extracts pain points, business opportunities, and automation ideas.
-   🏷️ **Dual-Layer Classification:** Categorizes each opportunity into a main category (e.g., `FinTech`) and a specific sub-category (e.g., `Payment Processing`).
-   💾 **Persistent Storage:** Saves all findings in a local SQLite database (`reddit_miner.db`).
-   📊 **Run & Batch Tracking:** Every execution is logged as a "run," and opportunities are linked to the run in which they were found.
-   🏃‍♂️ **Continuous Operation:** Can run continuously until a target number of new opportunities are found.
-   📈 **Powerful Reporting:** Provides a flexible reporting engine to generate percentage-based summaries by category, sub-category, and subreddit.

---

## 🛠️ Setup & Installation

1.  **Prerequisites:**
    -   Python 3.8+

2.  **Install Dependencies:**
    Install all the required Python packages using the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure API Keys:**
    -   Rename the `.env.example` file to `.env`.
    -   Open the `.env` file and add your API credentials for Groq and Reddit.

4.  **Initialize the Database:**
    Before running for the first time, you must initialize the database. This command creates the `reddit_miner.db` file and all necessary tables.
    ```bash
    python main.py db init
    ```
    **Note:** You must run this command again if the database schema is ever updated. This is a destructive operation that will reset all stored data.

---

## ▶️ How to Use

The tool is operated via the command line using three main commands: `run`, `report`, and `db`.

### 🏃‍♀️ `run`: Finding New Opportunities

This command starts a new analysis run to find and save opportunities.

**Usage:**
```bash
python main.py run <subreddit> -k <keyword1> <keyword2> ... [--target <number>]
