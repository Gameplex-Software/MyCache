import socket
import threading
import mysql.connector
import redis
import time

# MySQL database connection settings
mysql_config = {
    "host": "localhost",
    "port": int("3306"),
    "user": "admin",
    "password": "gam3p13xs0ftwar3",
    "database": "test"
}

# Redis cache configuration
redis_host = "localhost"
redis_port = 6379
redis_db = 0

# Caching settings
min_frequency = 10  # Minimum number of requests per hour to consider caching
cache_expiry = 3600  # Cache expiry time in seconds (1 hour)

# Initialize MySQL and Redis connections
mysql_connection = mysql.connector.connect(**mysql_config)
redis_connection = redis.Redis(host=redis_host, port=redis_port, db=redis_db)

def get_data_with_caching(self, query):
    cached_data = redis_connection.get(query)
    
    if cached_data:
        print("Retrieving data from Redis cache:")
        return cached_data.decode('utf-8')
    
    print("Fetching data from MySQL:")
    data = self.get_data_from_mysql(query)
        
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

def expire_old_cached_content(self):
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
    # MySQL protocol handshake
    client_handshake = client_socket.recv(1024)
    client_socket.sendall(b'\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00')

    # MySQL protocol command
    while True:
        command_packet = client_socket.recv(1024)
        if not command_packet:
            break
        
        # Extract the query from the command packet
        query = command_packet[5:].decode('utf-8')
        
        result = get_data_with_caching(query)
        
        # MySQL protocol result
        response_packet = construct_response_packet(result)
        client_socket.sendall(response_packet)

        # Update last access time for the query
        redis_connection.set(f"last_access:{query}", time.time())
        
        # Perform cache cleanup
        expire_old_cached_content()

    client_socket.close()

def construct_response_packet(result):
    result_length = len(result)
    response_packet = bytearray()
    response_packet.extend((result_length + 7).to_bytes(3, byteorder='little'))  # Packet length
    response_packet.extend(b'\x00\x00\x00\x02')  # Sequence number
    response_packet.extend((result_length + 1).to_bytes(3, byteorder='little'))  # Length of string
    response_packet.extend(b'\x00')  # Status
    response_packet.extend(result.encode('utf-8'))  # Result

    return response_packet

if __name__ == "__main__":
    proxy_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_server.bind(("0.0.0.0", 3308))
    proxy_server.listen(5)

    try:
        print("Proxy MySQL Server is running...")
        while True:
            client_socket, client_address = proxy_server.accept()
            threading.Thread(target=handle_client, args=(client_socket,)).start()
    except KeyboardInterrupt:
        print("\nShutting down the server...")
        proxy_server.close()
