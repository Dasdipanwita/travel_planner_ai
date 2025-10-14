# src/llm_handler.py
import json
import requests
import time
from src.config import Config

MODEL_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"

def call_llm_for_refinement(structured_plan, user_request):
    """
    Uses the Hugging Face Inference API to refine the plan, with better error handling.
    Falls back to a simple template if API fails.
    """
    if not Config.HF_TOKEN:
        return {"error": "Hugging Face Token is missing. Please set it in your .env file."}

    # Try API first
    try:
        result = _call_huggingface_api(structured_plan, user_request)
        if "error" not in result:
            print("✅ Successfully used AI API for itinerary generation")
            return result
        else:
            print(f"⚠️ API returned error, using fallback: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ API call failed, using fallback: {e}")

    # Fallback to simple template
    print("🔄 Using enhanced fallback itinerary")
    print(f"📊 Structured plan keys: {list(structured_plan.keys())}")
    for day_key, activities in structured_plan.items():
        print(f"📋 {day_key}: {len(activities)} activities")
        for i, activity in enumerate(activities[:2]):  # Show first 2 activities
            print(f"   Activity {i+1}: {activity}")
    return _create_simple_itinerary(structured_plan, user_request)

def _call_huggingface_api(structured_plan, user_request):

    prompt = f"""
    You are NomadAI, a smart AI travel planner for students. Your task is to convert a structured itinerary into a fun, engaging, and practical travel plan.

    **User Constraints:**
    {json.dumps(user_request, indent=2)}

    **Candidate Itinerary:**
    {json.dumps(structured_plan, indent=2)}

    **Your Task:**
    Flesh out the itinerary into a day-by-day plan with timings and student-focused tips.
    Your final output MUST be a single, valid JSON object and nothing else. Do not add any text before or after the JSON block.

    **Required JSON Output Format:**
    {{
      "trip_name": "A catchy name for the trip",
      "summary": "A brief, exciting summary of the trip.",
      "daily_plan": [
        {{
          "day": 1,
          "theme": "A theme for the day",
          "activities": [
            {{
              "time": "e.g., 09:00 AM",
              "activity": "Name of the place",
              "description": "A short, engaging description with a student-focused tip."
            }}
          ]
        }}
      ]
    }}

    **JSON Response:**
    """

    headers = {"Authorization": f"Bearer {Config.HF_TOKEN}"}
    payload = {
        "inputs": prompt,
    }

    try:
        response = requests.post(MODEL_URL, headers=headers, json=payload, timeout=120)

        # --- IMPROVED ERROR HANDLING ---
        # Check if the response is empty or not valid JSON
        if not response.text.strip():
            return {"error": "The AI model returned an empty response. This often means it's still loading. Please wait a minute and try again."}

        # Check response status code first
        if response.status_code != 200:
            return {"error": f"API request failed with status code {response.status_code}. Please check your token and try again."}

        # Try to parse the JSON
        try:
            response_json = response.json()
        except json.JSONDecodeError:
            return {"error": "The API returned invalid JSON. Please try again in a few moments."}

        # Assuming a successful response from here
        result_text = response_json[0]['generated_text']

        # Clean the response to ensure it's valid JSON
        if '{' in result_text and '}' in result_text:
            json_str = result_text[result_text.find('{'):result_text.rfind('}')+1]
        else:
            return {"error": "The AI model didn't return a proper JSON response. Please try again."}

        return json.loads(json_str)

    except requests.exceptions.RequestException as e:
        return {"error": f"A network error occurred: {e}"}
    except (ValueError, json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing JSON from Hugging Face API: {e}")
        return {"error": "The AI returned an invalid format. You can try generating it again."}

def _create_simple_itinerary(structured_plan, user_request):
    """
    Creates a realistic itinerary as fallback when API fails.
    """
    destination = user_request.get('destination', 'Unknown Destination')
    duration = user_request.get('duration_days', 1)
    interests = user_request.get('interests', [])

    # Create a more engaging structure
    trip_name = f"{destination} Dreams & Discoveries"
    interests_text = ', '.join(interests) if interests else 'adventure and culture'
    summary = f"Embark on a magical {duration}-day journey through {destination}, where every moment is crafted for curious students like you. Experience the perfect blend of {interests_text} that will create memories to last a lifetime! 🌟✨"

    daily_plan = []
    day_number = 1

    # Realistic time slots for activities
    time_slots = ["08:00 AM", "09:30 AM", "11:00 AM", "02:00 PM", "04:00 PM", "07:00 PM"]

    for day_key, activities in structured_plan.items():
        if day_key.startswith('day'):
            day_activities = []
            slot_index = 0

            # Group activities by type for better flow
            nature_activities = [a for a in activities if a.get('type') == 'nature']
            food_activities = [a for a in activities if a.get('type') == 'food']
            culture_activities = [a for a in activities if a.get('type') == 'culture']
            activity_activities = [a for a in activities if a.get('type') == 'activity']

            # Generate hotel information for this destination
            hotel_name = _get_hotel_for_destination(destination)

            # Start day with hotel departure
            day_activities.append({
                "time": "08:00 AM",
                "activity": f"🏨 Departure from {hotel_name}",
                "description": f"🚐 Check out from {hotel_name} and begin your adventure! Make sure to carry water, sunscreen, and comfortable walking shoes. Travel tip: Keep your student ID handy for potential discounts at various attractions."
            })

            # Create a logical daily flow
            current_slot = 1  # Start from second slot since first is hotel departure

            # Morning: Nature activities (best time for outdoor activities)
            for activity in nature_activities[:2]:  # Limit to 2 nature activities per day
                if current_slot < len(time_slots):
                    activity_name = activity.get('name', 'Beautiful Nature Spot')
                    if activity_name == 'Unknown Place':
                        activity_name = f"Mystical {activity.get('type', 'nature').title()} Destination"

                    day_activities.append({
                        "time": time_slots[current_slot],
                        "activity": activity_name,
                        "description": f"🌅 Arrive and immerse yourself in the breathtaking beauty of {activity_name}. Let the fresh morning air energize your soul as you explore this natural paradise. Perfect for students who want to connect with nature's tranquility. 💰 Entry: ₹{activity.get('cost', 0)} | ⏱️ Duration: ~2 hours | 📍 Located in the heart of {destination}"
                    })
                    current_slot += 1

            # Midday: Cultural activities
            for activity in culture_activities[:1]:  # Limit to 1 culture activity per day
                if current_slot < len(time_slots):
                    activity_name = activity.get('name', 'Cultural Heritage Site')
                    if activity_name == 'Unknown Place':
                        activity_name = f"Ancient {activity.get('type', 'culture').title()} Landmark"

                    day_activities.append({
                        "time": time_slots[current_slot],
                        "activity": activity_name,
                        "descriptison": f"🏛️ Step into history at {activity_name}, where ancient stories whisper through the stones. This cultural treasure offers students a fascinating glimpse into the rich heritage that shaped this incredible destination. 💰 Entry: ₹{activity.get('cost', 0)} | ⏱️ Duration: ~1.5 hours | Tip: Student discounts often available!"
                    })
                    current_slot += 1

            # Afternoon: General activities
            for activity in activity_activities[:2]:  # Limit to 2 general activities
                if current_slot < len(time_slots):
                    activity_name = activity.get('name', 'Adventure Hub')
                    if activity_name == 'Unknown Place':
                        activity_name = f"Exciting {activity.get('type', 'activity').title()} Experience"

                    day_activities.append({
                        "time": time_slots[current_slot],
                        "activity": activity_name,
                        "description": f"⚡ Feel the excitement build at {activity_name}! This is where adventure meets opportunity - perfect for students seeking thrills and new experiences that will become the highlight of your journey. 💰 Cost: ₹{activity.get('cost', 0)} | ⏱️ Duration: ~1 hour | Tip: Book in advance for group discounts!"
                    })
                    current_slot += 1

            # Evening: Food experiences
            for activity in food_activities[:1]:  # Limit to 1 food activity per day
                if current_slot < len(time_slots):
                    activity_name = activity.get('name', 'Local Eatery')
                    if activity_name == 'Unknown Place':
                        activity_name = f"Authentic {activity.get('type', 'food').title()} Haven"

                    day_activities.append({
                        "time": time_slots[current_slot],
                        "activity": activity_name,
                        "description": f"🌙 As the sun sets, treat yourself to the authentic flavors of {activity_name}. This culinary gem offers delicious, budget-friendly local cuisine that will delight your taste buds and create the perfect end to your day of exploration. 💰 Average meal: ₹{activity.get('cost', 0)} | ⏱️ Duration: ~1 hour | Tip: Try the local specialty!"
                    })
                    current_slot += 1

            # Fill remaining slots if needed
            remaining_activities = [a for a in activities if a not in nature_activities + food_activities + culture_activities + activity_activities]
            for activity in remaining_activities[:1]:  # Add one more if space
                if current_slot < len(time_slots):
                    activity_name = activity.get('name', 'Special Attraction')
                    if activity_name == 'Unknown Place':
                        activity_name = f"Unique {activity.get('type', 'attraction').title()} Gem"

                    day_activities.append({
                        "time": time_slots[current_slot],
                        "activity": activity_name,
                        "description": f"💎 Discover {activity_name}, a true hidden gem that most travelers miss. This special place adds that perfect touch of magic to your {destination} adventure, creating memories you'll treasure forever. 💰 Cost: ₹{activity.get('cost', 0)} | ⏱️ Duration: ~1 hour"
                    })

            # End day with hotel return
            day_activities.append({
                "time": "08:00 PM",
                "activity": f"🏨 Return to {hotel_name}",
                "description": f"🚐 Return to {hotel_name} for a well-deserved rest after an amazing day of exploration. Reflect on the day's adventures and get ready for tomorrow's discoveries. Sweet dreams in {destination}!"
            })

            # Create a theme based on the day and activities
            theme = f"Day {day_number}: "
            if nature_activities and culture_activities:
                theme += "Nature's Symphony & Cultural Harmony"
            elif nature_activities:
                theme += "Wild Wonders & Natural Beauty"
            elif culture_activities:
                theme += "Echoes of the Past"
            elif food_activities:
                theme += "Flavors of Tradition"
            elif activity_activities:
                theme += "Adventures & Excitement"
            else:
                theme += "Magical Discoveries Await"

            # Add some activities if the day is too empty
            if len(day_activities) < 3:  # Need at least hotel departure, one activity, hotel return
                day_activities.insert(1, {
                    "time": "10:00 AM",
                    "activity": f"{destination} Highlights",
                    "description": f"✨ Take time to explore the essence of {destination}. Wander, discover, and let the destination reveal its secrets to you. Every corner holds a story waiting to be uncovered by curious students like yourself."
                })

            daily_plan.append({
                "day": day_number,
                "theme": theme,
                "activities": day_activities
            })
            day_number += 1

    return {
        "trip_name": trip_name,
        "summary": summary,
        "daily_plan": daily_plan
    }

def _get_hotel_for_destination(destination):
    """Get appropriate hotel name for destination"""
    hotel_mapping = {
        'kashmir': 'Dal Lake Houseboat Resort',
        'goa': 'Beachside Backpackers Hostel',
        'kerala': 'Coconut Grove Homestay',
        'delhi': 'Connaught Place Youth Hostel',
        'mumbai': 'Gateway Backpackers Inn',
        'bangalore': 'Silicon Valley Student Lodge',
        'jaipur': 'Pink City Heritage Hotel',
        'agra': 'Taj View Budget Hotel',
        'varanasi': 'Ganges Riverside Hostel',
        'shimla': 'Mountain View Resort',
        'manali': 'Snow Valley Cottage',
        'darjeeling': 'Tea Garden Homestay',
        'ooty': 'Hill Station Lodge',
        'nainital': 'Lake View Hotel'
    }

    return hotel_mapping.get(destination.lower(), f'Comfortable Hostel in {destination}')