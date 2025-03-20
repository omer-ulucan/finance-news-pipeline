from scraping.rss_scraper import news_list
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline
import numpy as np
import time

embedder = pipeline("feature-extraction", model="bert-base-uncased", device=0)

def get_embedding(text, batch_size=8):
    features = embedder(text, batch_size=batch_size)
    embeddings = [np.mean(np.array(feature[0]), axis=0) for feature in features]
    return embeddings


def compute_lsh_hash(embedding, random_vectors):
    projection = np.dot(random_vectors, embedding)
    binary_hash = ''.join(np.where(projection >= 0, '1', '0'))
    return binary_hash


def remove_duplicates_lsh(news_list, threshold=0.85, num_hashes=20):
    embedding_dim = 768
    
    np.random.seed(48)
    
    random_vectors = np.random.rand(num_hashes, embedding_dim)
    
    texts = [news.get("title", "") + " " + news.get("summary", "") for news in news_list]
    embeddings = get_embedding(texts)
    
    for news, embedding in zip(news_list, embeddings):
        news["embedding"] = embedding
        news["lsh_hash"] = compute_lsh_hash(embedding, random_vectors)
    
    buckets = {}
    for news in news_list:
        key = news["lsh_hash"]
        buckets.setdefault(key, []).append(news)
        
    unique_news = []
    
    for bucket in buckets.values():
        bucket_unique = []
        for news in bucket:
            duplicate = False
            for unique in bucket_unique:
                sim = cosine_similarity([news["embedding"]],[unique["embedding"]])[0][0]
                if sim >=threshold:
                    duplicate= True
                    break
            if not duplicate:
                bucket_unique.append(news)
        unique_news.extend(bucket_unique)
    
    for news in unique_news:
        news.pop("embedding", None)
        news.pop("lsh_hash", None)
        
    return unique_news