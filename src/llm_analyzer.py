from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic.v1 import BaseModel, Field
from typing import List
from .config import api_keys
import json

# --- Category Definitions ---
CATEGORIES = {
    'SaaS': ['CRM', 'HR Tech', 'Project Management', 'BI & Analytics', 'MarTech', 'Customer Support', 'Collaboration', 'Vertical SaaS', 'API-as-a-Service', 'No-code/Low-code'],
    'E-commerce': ['Dropshipping Tools', 'Subscription Boxes', 'Personalized Products', 'Inventory Management', 'Logistics & Fulfillment', 'Headless Commerce', 'Live Shopping', 'Conversion Optimization'],
    'Health & Wellness': ['Telemedicine', 'Mental Health Apps', 'Fitness Trackers', 'Nutrition Planning', 'Wearables', 'Personalized Supplements', 'Sleep Tech', 'Corporate Wellness', 'FemTech'],
    'FinTech': ['Personal Finance', 'Robo-Advisors', 'P2P Lending', 'DeFi', 'Neobanks', 'Payment Processing', 'InsurTech', 'RegTech', 'Wealth Management', 'Expense Tracking'],
    'Education': ['Online Course Platforms (LMS)', 'Language Learning', 'AI Tutors', 'Virtual Labs', 'Test Prep', 'Skill-based Bootcamps', 'Special Needs Tech', 'Micro-learning'],
    'Developer Tools': ['CI/CD', 'Code Quality', 'API Management', 'Cloud Cost Management', 'Debugging Tools', 'Infrastructure as Code (IaC)', 'Security Scanning', 'Error Monitoring'],
    'AI/ML': ['No-code AI Platforms', 'Data Labeling', 'MLOps', 'AI-driven Analytics', 'Chatbot Builders', 'Recommendation Engines', 'NLP Services', 'Synthetic Data Generation'],
    'Productivity': ['Task Management', 'Note-taking Apps', 'Calendar & Scheduling', 'Habit Trackers', 'Personal Knowledge Management (PKM)', 'Email Management', 'Automation Tools'],
    'Marketing': ['Social Media Management', 'SEO Tools', 'Email Automation', 'Content Marketing', 'Affiliate Management', 'Influencer Platforms', 'Customer Data Platforms (CDP)'],
    'Content Creation': ['Video Editing', 'Graphic Design', 'Writing Assistants', 'Podcast Editing', 'Streaming Tools', 'Monetization Platforms', 'Newsletter Platforms'],
    'Gaming': ['Indie Game Dev Tools', 'Esports Coaching', 'In-game Asset Marketplaces', 'Cloud Gaming', 'AI-powered NPCs', 'Modding Platforms', 'Game Discovery', 'Fitness Gaming'],
    'Real Estate': ['Property Management', 'Virtual Tours', 'Investment Crowdfunding', 'iBuyer Platforms', 'Real Estate CRM', 'Mortgage Tech', 'Construction Tech (ConTech)'],
    'Travel': ['Itinerary Planners', 'Budget Travel Tools', 'Sustainable Tourism', 'AI Travel Agents', 'Last-minute Deals', 'Corporate Travel', 'Local Experience Marketplaces'],
    'Social Media': ['Niche Social Networks', 'Content Scheduling', 'Social Listening', 'User-Generated Content (UGC) Platforms', 'Creator Monetization', 'Decentralized Social Media'],
    'Other': ['Miscellaneous', 'Uncategorized']
}

# --- Pydantic Model for Structured Output ---
class OpportunityAnalysis(BaseModel):
    pain_points: List[str] = Field(description="List of specific problems or frustrations mentioned by users.")
    business_opportunities: List[str] = Field(description="Potential products or services to solve the pain points.")
    automation_ideas: List[str] = Field(description="Specific ways automation or AI could address the needs.")
    confidence_score: int = Field(description="A score from 1-10 on how promising this opportunity is.")
    summary: str = Field(description="A brief summary of the opportunity.")
    category: str = Field(description=f"The single most relevant business category. Must be one of: {', '.join(CATEGORIES.keys())}")
    sub_category: str = Field(description="The single most relevant sub-category from the chosen category. Must be a valid sub-category for the selected category.")

class LLMAnalyzer:
    """
    Uses a LangChain model to analyze Reddit posts and return structured JSON.
    """
    def __init__(self):
        self.llm = ChatGroq(
            model_name="llama-3.3-70b-versatile",
            groq_api_key=api_keys.get("groq_api_key"),
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        self.parser = JsonOutputParser(pydantic_object=OpportunityAnalysis)
        self.prompt_template = self._create_prompt_template()
        self.chain = self.prompt_template | self.llm | self.parser

    def _create_prompt_template(self):
        """
        Creates the prompt template for the LLM to output JSON.
        """
        # Format the categories and sub-categories for the prompt
        category_text = json.dumps(CATEGORIES, indent=2)

        template = '''
        You are an expert business analyst. Your task is to analyze the following Reddit post and its comments
        to identify potential business opportunities and classify them.

        **Post Title:** {post_title}
        **Post Body:** {post_body}

        **Top Comments:**
        {comments}

        **Instructions:**
        1.  Analyze the content to identify user pain points, potential business ideas, and automation opportunities.
        2.  First, choose the single most relevant **main category** for the opportunity from the keys in the JSON structure below.
        3.  Second, choose the single most relevant **sub-category** from the list corresponding to your chosen main category.
        4.  Provide your full analysis as a JSON object that strictly follows the format instructions.

        **Category and Sub-Category Structure:**
        ```json
        {category_structure}
        ```

        {format_instructions}
        '''
        return ChatPromptTemplate.from_template(
            template,
            partial_variables={
                "format_instructions": self.parser.get_format_instructions(),
                "category_structure": category_text
            }
        )

    def analyze_post(self, post_title: str, post_body: str, comments: List[str]) -> dict:
        """
        Analyzes a single post and returns a structured dictionary.
        """
        comment_text = "\n".join([f"- {comment}" for comment in comments])
        return self.chain.invoke({
            "post_title": post_title,
            "post_body": post_body,
            "comments": comment_text
        })