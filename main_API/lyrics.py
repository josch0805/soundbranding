import json
import os
import openai
from typing import List, Dict

# Initialize OpenAI API
openai.api_key = os.getenv('OPENAI_API_KEY')

def generate_lyrics(idea: str, company: str, name: str) -> str:
    """
    Generate lyrics using OpenAI's API based on the provided idea.
    
    Args:
        idea (str): The idea for the lyrics
        company (str): Company name
        name (str): Requester's name
        
    Returns:
        str: Generated lyrics
    """
    try:
        prompt = f"""Create a song lyrics based on the following idea:
        
        Company: {company}
        Requester: {name}
        Idea: {idea}
        
        Please create engaging and creative lyrics that capture the essence of the idea.
        The lyrics should be structured in verses and a chorus.
        Make it professional and suitable for commercial use."""
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional songwriter. Create engaging and creative lyrics."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"Error generating lyrics: {str(e)}")
        return ""

def process_approved_requests():
    # Path to the JSON file
    json_file = 'anfragen.json'
    
    try:
        # Read the JSON file
        with open(json_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        approved_requests = []
        
        # Process each request
        for request in data:
            # Check if the request has a status field and it's "freigegeben"
            if 'status' in request and request['status'] == 'freigegeben':
                # Extract the required information
                approved_info = {
                    'Firma': request['Firma'],
                    'Name': request['Name'],
                    'Idee': request['Idee']
                }
                
                # Generate lyrics for the approved request
                lyrics = generate_lyrics(
                    idea=request['Idee'],
                    company=request['Firma'],
                    name=request['Name']
                )
                
                # Add the generated lyrics to the request info
                approved_info['lyrics'] = lyrics
                approved_requests.append(approved_info)
                
                # Update the status to "in Bearbeitung"
                request['status'] = 'in Bearbeitung'
        
        # Save the updated data back to the file
        with open(json_file, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        
        return approved_requests
    
    except FileNotFoundError:
        print(f"Error: The file {json_file} was not found.")
        return []
    except json.JSONDecodeError:
        print("Error: The file contains invalid JSON.")
        return []
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return []

if __name__ == "__main__":
    # Example usage
    approved = process_approved_requests()
    if approved:
        print("Approved requests processed:")
        for request in approved:
            print(f"Company: {request['Firma']}")
            print(f"Name: {request['Name']}")
            print(f"Idea: {request['Idee']}")
            print("Generated Lyrics:")
            print(request['lyrics'])
            print("---")
    else:
        print("No approved requests found or an error occurred.")
