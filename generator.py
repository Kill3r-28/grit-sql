import os
import requests
import chromadb
from dotenv import load_dotenv

#loading the hidden api key from .env file
load_dotenv()

# Configuration
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise SystemExit("Error: OPENAI_API_KEY not found. Please check your .env file.")

def ask_openai(prompt_text):
    """Helper function to talk directly to OpenAI without an SDK."""
    url = "https://api.openai.com/v1/chat/completions"
    
    # OpenAI requires the key to be sent as a secure "Bearer" token in the headers
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # OpenAI expects a "messages" list with roles (user vs. system)
    data = {
        "model": "gpt-4o-mini",  # You can also use "gpt-4o-mini" to save money
        "messages": [
            {"role": "user", "content": prompt_text}
        ]
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    # 1. Check if the internet call failed (e.g., bad keys or zero credits)
    if response.status_code != 200:
        print("\n[!] OPENAI API ERROR:")
        print(response.text)
        raise SystemExit("Stopping script due to web error.")
        
    response_data = response.json()
    
    # 2. Safely extract the text from OpenAI's specific response structure
    try:
        return response_data["choices"][0]["message"]["content"]
    except KeyError:
        print("\n[!] UNEXPECTED RESPONSE FORMAT: OpenAI did not return text.")
        print(response_data)
        raise SystemExit("Stopping script due to missing content.")


def main():
    # 1. Get the raw request from the user
    user_prompt = input("Enter what kind of quiz you want to generate: ")

    # 2. Ask Gemini to turn the user's prompt into a clean search topic
    search_generation_prompt = f"""
    The user wants a quiz about: '{user_prompt}'. 
    Extract or summarize this request into a clean 2-3 word technical topic phrase that we can use to search a database.
    Respond with ONLY the phrase, nothing else.
    """
    search_query = ask_openai(search_generation_prompt).strip()
    print(f"\n-> Optimized search phrase: {search_query}")

    # 3. Connect directly to the database folder on your hard drive
    client = chromadb.PersistentClient(path="./anti_examples_db")
    collection = client.get_or_create_collection(
        name="sql_questions_already_in_db"
    )

    # 4. Fetch the top 10 matching questions
    search_results = collection.query(query_texts=[search_query], n_results=10)
    existing_questions_list = search_results["documents"][0]

    # 5. Format the context string into the matching questions block
    anti_examples = ""
    for index, question in enumerate(existing_questions_list):
        anti_examples += f"\n=== Matching Result #{index + 1} ===\n{question}\n"
        anti_examples += "\n" + "=" * 40 + "\n"

    print("\n--- ANTI-EXAMPLES FOUND ---")
    print(anti_examples)
    
    # The script will freeze here until you type 'y' and press Enter
    approval = input("\nDo these anti-examples look good? Type 'y' to proceed, or anything else to cancel: ")
    
    if approval.lower() != 'y':
        raise SystemExit("Script stopped by user.")

    # 6. Build the final prompt combining instructions and the database context
    final_prompt = f"""
    You are an expert SQL instructor. Your goal is to create a dynamic, brand-new multiple choice question based on the user's request: {user_prompt}.

    CRITICAL RULE: You must NOT replicate, copy, or closely mimic the style, scenario, or setup of the existing questions listed below. Use a completely different context, different table structure, and an entirely different angle of the concept to keep our quiz pool creative and diverse.

    Here is the context of 10 existing questions you must avoid repeating:
    {anti_examples}

    Please provide the new unique question, 4 options, and clearly state the correct answer.
    """

    # 7. Generate and display the final creative result
    print("\n-> Generating a completely unique question...")
    final_output = ask_openai(final_prompt)

    print("\n" + "#" * 50)
    print("FINAL GENERATED QUESTION:")
    print("#" * 50 + "\n")
    print(final_output)


if __name__ == "__main__":
    main()
