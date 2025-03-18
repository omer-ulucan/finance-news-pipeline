from scraping.rss_scraper import news_list
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline
import numpy as np
import time

embedder = pipeline("feature-extraction", model="bert-base-uncased")

def get_embedding(text):
    features = embedder(text)
    token_embeddings = np.array(features[0])
    avg_embedding = np.mean(token_embeddings, axis=0)
    return avg_embedding

def compute_lsh_bash(embedding, random_vectors):
    projection = np.dot(random_vectors, embedding)
    binary_hash = ''.join(['1' if x >= 0 else '0' for x in projection])
    return binary_hash

def remove_duplicates_lsh(news_list, threshold=0.85, num_hashes=20):
    embedding_dim = 768
    random_vectors = np.random.rand(num_hashes, embedding_dim)
    
    for news in news_list:
        combined_text = news.get("title", "") + " "+ news.get("summary", "")
        news["embedding"] = get_embedding(combined_text)
        news["lsh_hash"] = compute_lsh_bash(news["embedding"], random_vectors)
        
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

if __name__ == "__main__":
    # Örnek haber listesi: her haber bir sözlük
    # news_list örneğin rss_scraper'dan gelmiş ham haberler dizisi olsun.
    # Burada basit bir örnek liste oluşturduk.
    news_list = [
        {"title": "FED faiz artırımı yapıldı", "summary": "ABD Merkez Bankası faiz oranlarını yükseltti..."},
        {"title": "FED faiz artırımı yapıldı", "summary": "ABD Merkez Bankası, faiz oranlarını artırarak..."},
        {"title": "Ekonomi büyüyor", "summary": "Ülkede ekonomik büyüme rakamları umut verici..."}
    ]
    
    start_time = time.time()
    unique = remove_duplicates_lsh(news_list)
    elapsed = time.time() - start_time
    print(f"Duplicate kontrolü sonrası {len(unique)} benzersiz haber bulundu. İşlem süresi: {elapsed:.2f} saniye")