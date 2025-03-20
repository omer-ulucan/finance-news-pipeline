"""
News filtering module with duplicate detection
"""
from transformers import pipeline
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize BERT embedder
try:
    embedder = pipeline("feature-extraction", model="bert-base-uncased", device=0)
    logging.info("Device set to use cuda:0")
except RuntimeError:
    embedder = pipeline("feature-extraction", model="bert-base-uncased", device=-1)
    logging.info("CUDA unavailable, using CPU")

def get_embedding(text, batch_size=8, max_length=512):
    """
    Get BERT embeddings for text.
    
    Args:
        text: List of text strings to embed
        batch_size: Batch size for processing
        max_length: Maximum sequence length (BERT max is 512)
        
    Returns:
        List of embeddings
    """
    # Truncate texts to avoid exceeding BERT's token limit
    truncated_texts = []
    for t in text:
        # Rough estimate: assume average token is ~4 chars, limit to ~480 tokens to be safe
        # This gives us ~1920 chars (allowing some room for tokenization differences)
        if len(t) > 1900:
            truncated_texts.append(t[:1900] + "...")
        else:
            truncated_texts.append(t)
    
    try:
        features = embedder(truncated_texts, batch_size=batch_size, truncation=True, max_length=max_length)
        embeddings = [np.mean(np.array(feature[0]), axis=0) for feature in features]
        return embeddings
    except Exception as e:
        logging.error(f"Error during embedding: {e}")
        raise

def compute_lsh_hash(embedding, random_vectors):
    """
    Compute Locality-Sensitive Hashing (LSH) hash for an embedding.
    
    Args:
        embedding: Vector embedding of a news item
        random_vectors: Random projection vectors
        
    Returns:
        Binary hash string
    """
    projection = np.dot(random_vectors, embedding)
    binary_hash = ''.join(np.where(projection >= 0, '1', '0'))
    return binary_hash

def remove_duplicates_lsh(news_list, threshold=0.85, num_hashes=20):
    """
    Remove duplicate news using LSH and cosine similarity.
    
    Args:
        news_list: List of news items
        threshold: Similarity threshold (0.85 default)
        num_hashes: Number of hash functions
        
    Returns:
        List of unique news items
    """
    if not news_list:
        logging.warning("Empty news list provided to duplicate removal")
        return []
        
    logging.info(f"Starting duplicate removal for {len(news_list)} news items...")
    start_time = time.time()
    
    embedding_dim = 768  # BERT embedding dimension
    np.random.seed(48)  # For reproducibility
    random_vectors = np.random.rand(num_hashes, embedding_dim)
    
    # Create text representations by combining title and summary
    texts = []
    for news in news_list:
        title = news.get("title", "")
        summary = news.get("summary", "")
        # Ensure we don't make the text too long
        if len(summary) > 1500:
            summary = summary[:1500] + "..."
        texts.append(f"{title} {summary}")
    
    # Get embeddings
    try:
        embeddings = get_embedding(texts)
    except Exception as e:
        logging.error(f"Failed to get embeddings: {e}")
        return []  # Return empty list on error
    
    # Assign embeddings and compute hashes
    for news, embedding in zip(news_list, embeddings):
        news["embedding"] = embedding
        news["lsh_hash"] = compute_lsh_hash(embedding, random_vectors)
    
    # Group by hash bucket
    buckets = {}
    for news in news_list:
        key = news["lsh_hash"]
        buckets.setdefault(key, []).append(news)
    
    # Filter duplicates within each bucket
    unique_news = []
    for bucket in buckets.values():
        bucket_unique = []
        for news in bucket:
            duplicate = False
            for unique in bucket_unique:
                sim = cosine_similarity([news["embedding"]], [unique["embedding"]])[0][0]
                if sim >= threshold:
                    duplicate = True
                    break
            if not duplicate:
                bucket_unique.append(news)
        unique_news.extend(bucket_unique)
    
    # Clean up by removing embedding and hash
    for news in unique_news:
        news.pop("embedding", None)
        news.pop("lsh_hash", None)
    
    elapsed_time = time.time() - start_time
    logging.info(f"Removed {len(news_list) - len(unique_news)} duplicates in {elapsed_time:.2f} seconds")
    logging.info(f"Remaining unique news: {len(unique_news)}")
        
    return unique_news

def process_news():
    """
    Main function to process news: filter duplicates and add locations.
    """
    # Import here to avoid circular imports
    from scraping.rss_scraper import process_rss_feeds, news_list
    from modules.location_extractor import add_locations
    import asyncio
    
    # Remove duplicates
    start_time = time.time()
    filtered_news = remove_duplicates_lsh(news_list)
    filter_time = time.time() - start_time
    logging.info(f"Filtered {len(filtered_news)} unique news from {len(news_list)} total in {filter_time:.2f}s")
    
    # Add location information
    news_with_locations = add_locations(filtered_news)
    
    return news_with_locations

# If this file is run directly
if __name__ == "__main__":
    from scraping.rss_scraper import process_rss_feeds, news_list
    import asyncio
    
    # Collect news
    asyncio.run(process_rss_feeds())
    
    # Filter duplicates
    processed_news = remove_duplicates_lsh(news_list)
    
    # Print results
    logging.info(f"Processed {len(processed_news)} news items")
    if processed_news:
        sample = processed_news[0]
        logging.info(f"Sample: {sample['source']} - {sample.get('location', 'Unknown')} - {sample['title']}")