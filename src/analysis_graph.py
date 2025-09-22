from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Any
from datetime import datetime
from .reddit_client import RedditClient
from .llm_analyzer import LLMAnalyzer
from . import database
from tqdm import tqdm
import json

class GraphState(TypedDict):
    run_id: int
    subreddit: str
    keywords: List[str]
    time_period: str
    start_date: str
    end_date: str
    posts: List[dict]
    filtered_posts: List[dict]
    analysis_results: List[dict]
    after: str 
    new_opportunities_count: int

class AnalysisGraph:
    def __init__(self):
        self.reddit_client = RedditClient()
        self.llm_analyzer = LLMAnalyzer()
        self.workflow = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(GraphState)

        builder.add_node("route_data_source", self.route_data_source)
        builder.add_node("fetch_new_posts", self.fetch_new_posts)
        builder.add_node("fetch_historical_posts", self.fetch_historical_posts)
        builder.add_node("filter_posts", self.filter_posts)
        builder.add_node("analyze_posts", self.analyze_posts)
        builder.add_node("save_to_database", self.save_to_database)

        builder.set_entry_point("route_data_source")

        builder.add_conditional_edges(
            "route_data_source",
            self.decide_data_source,
            {"recent": "fetch_new_posts", "historical": "fetch_historical_posts"},
        )

        builder.add_edge("fetch_new_posts", "filter_posts")
        builder.add_edge("fetch_historical_posts", "filter_posts")
        builder.add_edge("filter_posts", "analyze_posts")
        builder.add_edge("analyze_posts", "save_to_database")
        builder.add_edge("save_to_database", END)

        return builder.compile()

    def decide_data_source(self, state: GraphState):
        if state["time_period"] == "recent":
            return "recent"
        return "historical"

    def route_data_source(self, state: GraphState):
        print("---ROUTING DATA SOURCE---")
        if any(char.isdigit() for char in state["time_period"]):
            state["time_period"] = "historical"
            year = int(''.join(filter(str.isdigit, state["time_period"])))
            state["start_date"] = f"{year}-01-01"
            state["end_date"] = f"{year}-12-31"
        else:
            state["time_period"] = "recent"
        return state

    def fetch_new_posts(self, state: GraphState):
        print(f"---FETCHING NEW POSTS for r/{state['subreddit']}---")
        posts_praw, after_token = self.reddit_client.get_new_posts(
            state["subreddit"], 
            limit=100,
            after=state.get("after")
        )
        print(f"Fetched {len(posts_praw)} posts.")
        
        # Extract required data, including the creation timestamp
        posts_data = [
            {
                "id": p.id, "title": p.title, "selftext": p.selftext, 
                "score": p.score, "num_comments": p.num_comments, "url": p.url,
                "created_utc": datetime.fromtimestamp(p.created_utc) # Convert to datetime
            } 
            for p in posts_praw
        ]
        state["posts"] = posts_data
        state["after"] = after_token
        return state

    def fetch_historical_posts(self, state: GraphState):
        print(f"---FETCHING HISTORICAL POSTS for r/{state['subreddit']}---")
        posts_pushshift = self.reddit_client.get_historical_posts(
            state["subreddit"], state["keywords"], state["start_date"], state["end_date"]
        )
        
        # Extract and convert timestamp
        posts_data = [
            {
                "id": p.get("id"), "title": p.get("title"), "selftext": p.get("selftext"),
                "score": p.get("score"), "num_comments": p.get("num_comments"), "url": p.get("full_link"),
                "created_utc": datetime.fromtimestamp(p.get("created_utc")) # Convert to datetime
            }
            for p in posts_pushshift
        ]
        state["posts"] = posts_data
        return state

    def filter_posts(self, state: GraphState):
        print("---FILTERING POSTS---")
        
        filtered = [
            p for p in state["posts"]
            if p.get("num_comments", 0) > 5
        ]
        
        if state["time_period"] == "recent":
            keywords = [k.lower() for k in state["keywords"]]
            filtered = [
                p for p in filtered
                if any(k in p.get("title", "").lower() or k in p.get("selftext", "").lower() for k in keywords)
            ]

        print(f"Found {len(state['posts'])} posts, filtered down to {len(filtered)}.")
        state["filtered_posts"] = filtered
        return state

    def analyze_posts(self, state: GraphState):
        print("---ANALYZING POSTS WITH LLM---")
        results = []
        if not state["filtered_posts"]:
            state["analysis_results"] = []
            return state

        for post in tqdm(state["filtered_posts"], desc="Analyzing Posts"):
            try:
                comments_praw = self.reddit_client.get_comments(post["id"])
                comment_bodies = [c.body for c in comments_praw]
                
                analysis_dict = self.llm_analyzer.analyze_post(
                    post_title=post["title"],
                    post_body=post.get("selftext", ""),
                    comments=comment_bodies
                )
                
                # Add post metadata to the analysis results
                analysis_dict['url'] = post.get("url")
                analysis_dict['title'] = post.get("title")
                analysis_dict['post_created_utc'] = post.get("created_utc") # Pass date through

                # Convert lists to JSON strings for DB storage
                analysis_dict['pain_points'] = json.dumps(analysis_dict.get('pain_points', []))
                analysis_dict['business_opportunities'] = json.dumps(analysis_dict.get('business_opportunities', []))
                analysis_dict['automation_ideas'] = json.dumps(analysis_dict.get('automation_ideas', []))

                results.append(analysis_dict)
            except Exception as e:
                print(f"Could not analyze or parse post {post.get('id')}: {e}")
        state["analysis_results"] = results
        return state

    def save_to_database(self, state: GraphState):
        print("---SAVING RESULTS TO DATABASE---")
        if not state["analysis_results"]:
            print("No results to save.")
            state["new_opportunities_count"] = 0
            return state
        
        run_id = state["run_id"]
        new_count = 0
        for result in tqdm(state["analysis_results"], desc="Saving to DB"):
            is_new = database.insert_opportunity(run_id, result)
            if is_new:
                new_count += 1
        
        print(f"Saved {new_count} new opportunities to the database for run ID {run_id}.")
        state["new_opportunities_count"] = new_count
        return state

    def run(self, initial_state: dict):
        return self.workflow.invoke(initial_state)
