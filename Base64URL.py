import base64

def encode_base64url(data):
    # Base64 を URL-safe にエンコードして、末尾の "=" を取り除く
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip("=")

# public_key.pem を開く
with open("public_key.pem", "rb") as f:
    public_key = f.read()
    
    # Base64URL 形式に変換
    encoded_public_key = encode_base64url(public_key)
    print("Base64URL encoded public key:", encoded_public_key)
