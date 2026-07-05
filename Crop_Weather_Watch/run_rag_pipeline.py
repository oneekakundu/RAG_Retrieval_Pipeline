import argparse
from pathlib import Path

from rag_pipeline.pipeline import WeatherWatchRAGPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Weather Watch RAG preprocessing pipeline")
    parser.add_argument("--start-date", type=str, default=None, help="Start date in dd-mm-yyyy format")
    parser.add_argument("--end-date", type=str, default=None, help="End date in dd-mm-yyyy format")
    parser.add_argument("--limit", type=int, default=None, help="Optional cap on the number of reports to download per run")
    parser.add_argument("--query", type=str, default=None, help="Optional semantic search query after indexing")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent / "data"
    pipeline = WeatherWatchRAGPipeline(base_dir=base_dir)

    records = pipeline.downloader.fetch_metadata()

    if not args.start_date or not args.end_date:
        raise ValueError("Please provide both --start-date and --end-date in dd-mm-yyyy format")

    selected_records = pipeline.downloader.filter_by_date(records, args.start_date, args.end_date)

    if not selected_records:
        raise ValueError("No Weather Watch records were found for the requested date range")

    enriched_records = [
        {
            "Title": record.get("Title", f"weather-watch-{index + 1:02d}"),
            "document_path": record.get("document_path", ""),
            "PublishDate": record.get("PublishDate"),
            "PDF Link": "https://agriwelfare.gov.in" + record.get("document_path", ""),
        }
        for index, record in enumerate(selected_records)
    ]

    week_name = f"range_{args.start_date.replace('-', '')}_{args.end_date.replace('-', '')}"
    pipeline.process_reports(enriched_records, week_name=week_name, limit=args.limit)

    if args.query:
        print(pipeline.search(args.query, top_k=3))
    else:
        print("Pipeline completed successfully")
        print("You can now ask retrieval questions. Type 'exit' to quit.")
        while True:
            user_query = input("Enter your query: ").strip()
            if not user_query or user_query.lower() in {"exit", "quit"}:
                break
            results = pipeline.search(user_query, top_k=3)
            for item in results:
                print(f"\nChunk: {item['chunk_id']} | Page: {item['page_number']} | Score: {item['score']:.3f}")
                print(item['text'][:1200])


if __name__ == "__main__":
    main()
