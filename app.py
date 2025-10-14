# app.py
import streamlit as st
from src.planner import generate_itinerary

st.set_page_config(page_title="NomadAI Student Planner", page_icon="✈️")

# --- UI Elements ---
st.title("NomadAI ✈️")
st.markdown("Your smart travel planner for student-friendly, budget trips!")

with st.sidebar:
    st.header("Build Your Trip")
    destination = st.text_input("Destination", "Darjeeling", help="Currently only Darjeeling is supported.")
    duration_days = st.number_input("How many days?", min_value=1, max_value=7, value=2)
    budget_inr = st.slider("What's your budget (in ₹)?", min_value=1000, max_value=20000, value=3000, step=500)
    
    all_interests = ["nature", "culture", "food", "activity"]
    interests = st.multiselect(
        "What are your interests?",
        options=all_interests,
        default=["nature", "food"]
    )

# --- Logic ---
if st.sidebar.button("Generate Itinerary 🚀"):
    if not interests:
        st.error("Please select at least one interest.")
    else:
        user_request = {
            "destination": destination,
            "duration_days": duration_days,
            "budget_inr": budget_inr,
            "interests": interests
        }
        
        with st.spinner("🤖 AI is crafting your personalized itinerary..."):
            final_plan = generate_itinerary(user_request)

        if "error" in final_plan:
            st.error(final_plan["error"])
        else:
            st.success("Your personalized itinerary is ready!")
            
            # Display Summary
            st.header(final_plan.get("trip_name", "Your Trip"))
            st.markdown(f"**Budget Status:** {final_plan.get('budget_compliance')}")
            st.markdown(f"**Estimated Cost:** {final_plan.get('estimated_total_cost')}")
            st.info(f"**Summary:** {final_plan.get('summary', 'No summary available.')}")

            # Display Daily Plan
            for day_plan in final_plan.get("daily_plan", []):
                with st.expander(f"**Day {day_plan['day']}: {day_plan['theme']}**", expanded=True):
                    for activity in day_plan["activities"]:
                        st.markdown(f"**🕒 {activity['time']} - {activity['activity']}**")
                        st.write(activity['description'])
                        st.divider()