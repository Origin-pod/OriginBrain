import argparse
import sys
import logging
from src.brain.vector_store import BrainDB

# Configure logging to suppress verbose output for CLI
logging.basicConfig(level=logging.ERROR)

def search(query):
    print(f"Searching for: '{query}'...")
    try:
        db = BrainDB()
        results = db.search(query)
        
        if not results or not results['documents']:
            print("No results found.")
            return

        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]
        
        print(f"\nFound {len(documents)} results:\n")
        
        for i, doc in enumerate(documents):
            meta = metadatas[i]
            score = distances[i]
            print(f"[{i+1}] Score: {score:.4f}")
            print(f"Source: {meta.get('source_url', 'Unknown')}")
            print(f"Date: {meta.get('created_at', 'Unknown')}")
            print("-" * 40)
            print(doc[:500] + "..." if len(doc) > 500 else doc)
            print("=" * 60 + "\n")
            
    except Exception as e:
        print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="OriginSteward CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Search Command
    search_parser = subparsers.add_parser("search", help="Search your brain")
    search_parser.add_argument("query", type=str, help="The search query")
    
    args = parser.parse_args()
    
    if args.command == "search":
        search(args.query)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
