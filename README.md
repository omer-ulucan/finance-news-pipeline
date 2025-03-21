# RSS News Tracker with Location Extraction

A high-performance system for collecting news from multiple RSS sources, removing duplicates, and automatically extracting location information from article content.

## Features

- **Multi-source RSS Collection**: Fetches news from multiple RSS feeds defined in a configuration file
- **Duplicate Detection**: Uses LSH (Locality-Sensitive Hashing) and BERT embeddings to efficiently detect and remove duplicate news
- **Automatic Location Extraction**: Analyzes article content to extract geographical locations using NLP
- **High Performance**:
  - Asynchronous processing of RSS feeds and article fetching
  - Parallel processing with optimized resource usage
  - Two-pass location extraction for maximum coverage
- **Robust Error Handling**: Comprehensive error handling and logging
- **Detailed Analytics**: Performance metrics and processing statistics

## Project Structure

```
project/
├── modules/
│   ├── location_extractor.py   # Location extraction using NLP
│   └── news_filter.py          # Duplicate detection and removal
├── news/
│   └── rss.json                # RSS sources configuration
├── scraping/
│   ├── rss_scraper.py          # RSS feed processing
│   └── main.py                 # Main execution script
├── logs/                       # Generated log files
├── results/                    # Output JSON files with processed news
├── README.md                   # Project documentation
└── requirements.txt            # Project dependencies
```

## Installation

### Prerequisites

- Python 3.7+
- pip package manager

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/rss-news-tracker.git
   cd rss-news-tracker
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Install the spaCy English language model for NLP:
   ```bash
   python -m spacy download en_core_web_sm
   ```

## Usage

### Basic Usage

Run the main script to collect, process news, and extract locations:

```bash
python main.py
```

The script will:

1. Collect news from all RSS sources defined in `news/rss.json`
2. Remove duplicate news items
3. Extract location information from each article
4. Save the processed news to a JSON file in the `results/` directory

### Output

The processed news will be saved as a JSON file in the `results/` directory with a timestamp:

```json
[
  {
    "source": "CNN",
    "title": "Example news headline",
    "link": "https://example.com/news/article",
    "published": "2023-03-20T14:30:00+00:00",
    "summary": "This is a summary of the news article...",
    "location": "Washington"
  }
  // More news items...
]
```

### Logs

Detailed logs are saved in the `logs/` directory. Each log file contains information about:

- Number of news items collected
- Duplicate removal statistics
- Location extraction success rate
- Performance metrics
- Sample processed news items

## Configuration

### RSS Sources

RSS sources are defined in `news/rss.json`:

```json
[
  {
    "source": "CNN",
    "rss_feeds": {
      "1": "http://rss.cnn.com/rss/edition_world.rss",
      "2": "http://rss.cnn.com/rss/money_news_economy.rss"
    }
  },
  {
    "source": "BBC",
    "rss_feeds": {
      "1": "http://feeds.bbci.co.uk/news/world/rss.xml"
    }
  }
  // More sources...
]
```

### Customization

The following parameters can be adjusted in their respective files:

#### Location Extraction (`modules/location_extractor.py`):

- `FIRST_PASS_TIMEOUT`: Timeout for the first pass of article fetching (default: 3s)
- `RETRY_TIMEOUT`: Timeout for the retry pass (default: 5s)
- `MAX_TEXT_LEN`: Maximum text length to analyze (default: 500 chars)

#### Duplicate Detection (`modules/news_filter.py`):

- `threshold`: Similarity threshold for duplicate detection (default: 0.85)
- `num_hashes`: Number of hash functions for LSH (default: 20)

## Technical Details

### Location Extraction

The location extraction process uses a two-pass approach:

1. **First Pass**: Quickly processes all articles with a short timeout
2. **Second Pass**: Retries failed articles with a longer timeout

For each article, the system:

1. Fetches the full article content using the link from RSS
2. Processes the text with spaCy's Named Entity Recognition
3. Extracts the first Geo-Political Entity (GPE) or Location (LOC)
4. Adds this location to the news item

### Duplicate Detection

The system uses an advanced duplicate detection method:

1. Generates BERT embeddings for news items (title + summary)
2. Applies LSH (Locality-Sensitive Hashing) to efficiently group similar items
3. Uses cosine similarity within each bucket to identify duplicates
4. Keeps only one item from each group of duplicates

## Performance Optimization

- **Asynchronous HTTP**: Uses `aiohttp` for parallel article fetching
- **Connection Pooling**: Optimizes connection reuse
- **Timeout Management**: Different timeouts for first pass and retry
- **Text Truncation**: Analyzes only the beginning of articles (locations usually appear early)
- **Minimal NLP Pipeline**: Disables unneeded spaCy components
- **Error Resilience**: Gracefully handles failures without stopping the entire process
