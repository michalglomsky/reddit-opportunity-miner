import argparse
import time
from src.analysis_graph import AnalysisGraph
from src.database import generate_report, initialize_db, create_run, list_runs

def main():
    """
    Main function to run the Reddit Opportunity Miner.
    """
    parser = argparse.ArgumentParser(
        description="Reddit Opportunity Miner - Find and analyze business opportunities on Reddit.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # --- Top-level commands ---
    subparsers = parser.add_subparsers(dest='command', required=True, help='Available commands')

    # --- 'run' command ---
    run_parser = subparsers.add_parser('run', help='Start a new analysis run to find opportunities.')
    run_parser.add_argument("subreddit", type=str, help="The subreddit to analyze (e.g., 'SaaS').")
    run_parser.add_argument("-k", "--keywords", nargs="+", required=True, help="Keywords to search for.")
    run_parser.add_argument("--target", type=int, default=10, help="Target number of NEW opportunities to find. Default: 10.")
    run_parser.add_argument("-t", "--time", default="recent", help="Time period: 'recent' for continuous scanning, or a year (e.g., '2022') for historical.")

    # --- 'report' command ---
    report_parser = subparsers.add_parser('report', help='Generate reports from the database.')
    report_parser.add_argument("report_type", choices=['category', 'subcategory', 'subreddit_bias'], help="The type of report to generate.")
    report_parser.add_argument("--run-ids", nargs='+', type=int, help="Filter by specific run IDs (e.g., 1 2 5).")
    report_parser.add_argument("--runs-after", type=str, help="Filter to runs executed ON or AFTER this date (YYYY-MM-DD).")
    report_parser.add_argument("--runs-before", type=str, help="Filter to runs executed ON or BEFORE this date (YYYY-MM-DD).")
    report_parser.add_argument("--posts-after", type=str, help="Filter to posts created ON or AFTER this date (YYYY-MM-DD).")
    report_parser.add_argument("--posts-before", type=str, help="Filter to posts created ON or BEFORE this date (YYYY-MM-DD).")
    report_parser.add_argument("--category", dest='category_filter', type=str, help="For 'subcategory' reports, specify the main category to inspect.")

    # --- 'db' command ---
    db_parser = subparsers.add_parser('db', help='Manage the database.')
    db_parser.add_argument("db_command", choices=['init', 'list_runs'], help="Database command to execute.")
    db_parser.add_argument("--runs-after", type=str, help="For 'list_runs', filter runs executed ON or AFTER this date (YYYY-MM-DD).")
    db_parser.add_argument("--runs-before", type=str, help="For 'list_runs', filter runs executed ON or BEFORE this date (YYYY-MM-DD).")


    args = parser.parse_args()

    if args.command == 'db':
        if args.db_command == 'init':
            confirm = input("WARNING: This will delete all existing data in reddit_miner.db. Continue? (y/n): ")
            if confirm.lower() == 'y':
                initialize_db()
            else:
                print("Database initialization cancelled.")
        elif args.db_command == 'list_runs':
            list_runs(runs_after=args.runs_after, runs_before=args.runs_before)
    
    elif args.command == 'report':
        if args.report_type == 'subcategory' and not args.category_filter:
            parser.error("--category is required for the 'subcategory' report type.")
        
        filters = {
            'report_type': args.report_type,
            'run_ids': args.run_ids,
            'runs_after': args.runs_after,
            'runs_before': args.runs_before,
            'posts_after': args.posts_after,
            'posts_before': args.posts_before,
            'category_filter': args.category_filter
        }
        generate_report(filters)

    elif args.command == 'run':
        run_command(args)


def run_command(args):
    print("Starting a new Reddit Opportunity Miner run...")
    try:
        keyword_str = ", ".join(args.keywords)
        run_id = create_run(subreddit=args.subreddit, keywords=keyword_str)
        print(f"Created new run with ID: {run_id}. Target: {args.target} new opportunities.")
        
        graph = AnalysisGraph()
        
        total_new_found = 0
        after_token = None
        batch_num = 0

        while total_new_found < args.target:
            batch_num += 1
            print(f"\n--- Starting Batch {batch_num} (Found {total_new_found}/{args.target}) ---")
            
            initial_state = {
                "run_id": run_id,
                "subreddit": args.subreddit,
                "keywords": args.keywords,
                "time_period": args.time,
                "after": after_token,
                "start_date": "", "end_date": "", "posts": [], "filtered_posts": [],
                "analysis_results": [], "new_opportunities_count": 0,
            }

            final_state = graph.run(initial_state)
            
            batch_new_count = final_state.get("new_opportunities_count", 0)
            total_new_found += batch_new_count
            
            after_token = final_state.get("after")

            if not after_token:
                print("--- Reached the end of available posts. Stopping run. ---")
                break
            
            if batch_new_count == 0 and args.time == 'recent':
                print("--- No new posts found in this batch. Waiting before retrying... ---")
                time.sleep(60) # Wait a minute if we're scanning for recent posts and find nothing

            time.sleep(2)

        print(f"\n--- Run {run_id} Complete ---")
        print(f"Target of {args.target} met or exceeded. Found a total of {total_new_found} new opportunities.")
        
        print("\nFinal analysis for this run:")
        generate_report(filters={'report_type': 'category', 'run_ids': [run_id]})

    except Exception as e:
        print(f"An error occurred during the run: {e}")


if __name__ == "__main__":
    main()
