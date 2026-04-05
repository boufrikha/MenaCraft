# Enhanced Image Reverse Search and Posting History Detection

import requests

class ImageSearch:
    def __init__(self, api_key):
        self.api_key = api_key

    def reverse_search(self, image_path):
        with open(image_path, 'rb') as image:
            response = requests.post(
                'https://api.gemini.com/reverse_search',
                headers={'Authorization': f'Bearer {self.api_key}'},
                files={'file': image}
            )
        return response.json()

class PostingHistory:
    def __init__(self, api_key):
        self.api_key = api_key

    def get_history(self, user_id):
        response = requests.get(
            f'https://api.gemini.com/users/{user_id}/posts',
            headers={'Authorization': f'Bearer {self.api_key}'},
        )
        return response.json()

# Usage Example
if __name__ == '__main__':
    image_search = ImageSearch(api_key='your_api_key')
    results = image_search.reverse_search('path_to_image.jpg')
    print(results)
    
    posting_history = PostingHistory(api_key='your_api_key')
    history = posting_history.get_history(user_id='user_id')
    print(history)