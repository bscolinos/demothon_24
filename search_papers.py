import arxiv
import os
import requests
import argparse
import sys

def sanitize_filename(filename):
    return "".join([c for c in filename if c.isalpha() or c.isdigit() or c==' ']).rstrip()

def download_arxiv_papers(query, max_results, output_dir):
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Create an API client
    client = arxiv.Client()

    # Define the search query
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )

    # Fetch the results
    results = client.results(search)

    # Download PDFs and print information for each result
    for paper in results:
        print(f"Title: {paper.title}")
        print(f"Authors: {', '.join(author.name for author in paper.authors)}")
        print(f"Published: {paper.published}")
        print(f"arXiv ID: {paper.entry_id}")
        
        # Download PDF
        pdf_url = paper.pdf_url
        response = requests.get(pdf_url)
        if response.status_code == 200:
            # Create a filename from the paper title
            filename = sanitize_filename(paper.title)[:50]  # Limit filename length
            filepath = os.path.join(output_dir, f"{filename}.pdf")
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"PDF downloaded: {filepath}")
        else:
            print(f"Failed to download PDF. Status code: {response.status_code}")
        
        print("\n---\n")

    print(f"PDFs have been downloaded to the '{output_dir}' directory.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download recent arXiv papers as PDFs.")
    parser.add_argument("query", help="Search query (e.g., 'cat:stat.ML OR cat:cs.LG' for machine learning)")
    parser.add_argument("--max_results", type=int, default=10, help="Maximum number of results to return")
    parser.add_argument("--output_dir", default="arxiv_pdfs", help="Directory to save the PDFs")
    
    args = parser.parse_args()

    download_arxiv_papers(args.query, args.max_results, args.output_dir)
