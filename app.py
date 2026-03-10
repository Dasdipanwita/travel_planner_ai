# app.py
from datetime import datetime

import pytz
import streamlit as st

from src.config import Config
from src.logger import get_logger
from src.planner import generate_itinerary


def convert_to_local_time(utc_time_str, timezone_str='Asia/Kolkata'):
    utc = pytz.utc
    local_tz = pytz.timezone(timezone_str)

    parse_formats = ['%H:%M:%S', '%H:%M', '%I:%M %p']
    parsed = None
    for fmt in parse_formats:
        try:
            parsed = datetime.strptime(utc_time_str, fmt)
            break
        except Exception:
            continue

    if parsed is None:
        return utc_time_str

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=utc)

    local_time = parsed.astimezone(local_tz)
    return local_time.strftime('%I:%M %p')


logger = get_logger(__name__)

st.set_page_config(page_title="NomadAI Student Planner", page_icon="✈️")

st.title("NomadAI ✈️")
st.markdown("Your smart travel planner for student-friendly, budget trips!")

with st.sidebar:
    st.header("Build Your Trip")
    destination = st.text_input("Destination", "Darjeeling", help="Try Darjeeling or any city. Geoapify API key required for live data.")
    duration_days = st.number_input("How many days?", min_value=1, max_value=7, value=2)
    budget_inr = st.slider("What's your budget (in ₹)?", min_value=1000, max_value=20000, value=3000, step=500)
    num_people = st.number_input("Number of travelers", min_value=1, max_value=10, value=1)

    all_interests = ["nature", "culture", "food", "activity"]
    interests = st.multiselect(
        "What are your interests?",
        options=all_interests,
        default=["nature", "food"]
    )

missing = Config.validate()
if missing:
    with st.sidebar:
        st.error(f"Missing environment variables: {', '.join(missing)}. Add them to .env or set them in your environment.")

if st.sidebar.button("Generate Itinerary 🚀"):
    if not interests:
        st.error("Please select at least one interest.")
    else:
        user_request = {
            "destination": destination,
            "duration_days": duration_days,
            "budget_inr": budget_inr,
            "interests": interests,
            "num_people": num_people,
        }

        with st.spinner("🤖 AI is crafting your personalized itinerary..."):
            final_plan = generate_itinerary(user_request)

        if "error" in final_plan:
            st.error(final_plan["error"])
        else:
            st.success("Your personalized itinerary is ready!")
            if final_plan.get('has_beach'):
                st.markdown("🏖️ **Beach included**")

            st.header(final_plan.get("trip_name", "Your Trip"))
            st.markdown(f"**Budget Status:** {final_plan.get('budget_compliance')}")
            st.markdown(f"**Estimated Total Cost:** {final_plan.get('estimated_total_cost')}")
            st.markdown(f"**Estimated Per Person:** {final_plan.get('estimated_per_person')}")
            st.markdown(f"**Estimate Range:** {final_plan.get('estimate_range')}")
            st.info(f"**Summary:** {final_plan.get('summary', 'No summary available.')}")

            for day_plan in final_plan.get("daily_plan", []):
                with st.expander(f"**Day {day_plan['day']}: {day_plan['theme']}**", expanded=True):
                    for activity in day_plan["activities"]:
                        local_time = convert_to_local_time(activity['time'])
                        st.markdown(f"**🕒 {local_time} - {activity['activity']}**")
                        st.write(activity.get('description', 'No description available.'))
                        st.divider()