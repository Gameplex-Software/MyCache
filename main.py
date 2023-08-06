import pymysql
import redis.
import time
import socket
import threading

# MySQL database connection settings
mysql_config = {
    "host": "your_mysql_host",
    "user": "your_mysql_user",
    "password": "your_mysql_password",
    "database": "your_mysql_database"
}

# Redis cache configuration
redis_host = "localhost"
redis_port = 6379
redis_db = 0

# Caching settings
min_frequency = 10  # Minimum number of requests per hour to consider caching
cache_expiry = 3600  # Cache expiry time in seconds (1 hour)

# Initialize MySQL and Redis connections
mysql_connection = pymysql.connect(**mysql_config)
redis_connection = redis.Redis(host=redis_host, port=redis_port, db=redis_db)

def get_data_from_mysql(query):
    cursor = mysql_connection.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return data

def get_data_with_caching(query):
    cached_data = redis_connection.get(query)
    
    if cached_data:
        print("Retrieving data from Redis cache:")
        return cached_data.decode('utf-8')
    
    print("Fetching data from MySQL:")
    data = get_data_from_mysql(query)
    
    # Calculate the frequency of access for this query
    query_frequency_key = f"query_frequency:{query}"
    current_time = time.time()
    redis_connection.zincrby("query_frequencies", 1, query_frequency_key)
    
    # Check if the query meets the caching threshold
    query_frequency = redis_connection.zscore("query_frequencies", query_frequency_key)
    if query_frequency and query_frequency >= min_frequency:
        # Store data in Redis cache
        redis_connection.setex(query, cache_expiry, str(data))
    
    return data

def expire_old_cached_content():
    current_time = time.time()
    # Find and remove old cached content
    for query in redis_connection.scan_iter(match="query:*"):
        last_access_time = redis_connection.get(f"last_access:{query}")
        if last_access_time and current_time - float(last_access_time) > cache_expiry:
            redis_connection.delete(query)
            redis_connection.delete(f"last_access:{query}")
    
    # Remove query frequency entries for queries that no longer exist
    for query_frequency_key in redis_connection.zrangebyscore("query_frequencies", 0, min_frequency):
        redis_connection.zrem("query_frequencies", query_frequency_key)

def handle_client(client_socket):
    client_query = client_socket.recv(4096).decode('utf-8')
    result = get_data_with_caching(client_query)
    client_socket.sendall(str(result).encode('utf-8'))

    # Update last access time for the query
    redis_connection.set(f"last_access:{client_query}", time.time())
        
    # Perform cache cleanup
    expire_old_cached_content()

    client_socket.close()

if __name__ == "__main__":
    proxy_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_server.bind(("0.0.0.0", 3306))
    proxy_server.listen(5)

    try:
        print("Proxy MySQL Server is running...")
        while True:
            client_socket, client_address = proxy_server.accept()
            threading.Thread(target=handle_client, args=(client_socket,)).start()
    except KeyboardInterrupt:
        print("\nShutting down the server...")
        proxy_server.close()
