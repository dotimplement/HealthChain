import streamlit as st
from healthchain.data_generator.encounter_generator import EncounterGenerator


def main():
    st.title("My Streamlit App")
    st.write("Welcome to my app!")
    st.write("This app generates synthetic health data.")
    st.write(
        "The data is generated using the `EncounterGenerator` class from the `healthchain` package."
    )

    # Create an instance of the EncounterGenerator class
    with st.sidebar:
        st.write("### Encounter Generator")
        st.write("Use the EncounterGenerator to generate synthetic health data.")
        st.write("Click the button below to generate a synthetic encounter.")
        # TODO: Hardcode these strings to avoid typos
        selected_set = st.selectbox(
            "Select a workflow", ["encounter-discharge", "patient-view"]
        )

    generator = EncounterGenerator()

    # Generate a synthetic encounter on button click
    if st.button("Generate Encounter"):
        encounter = generator.generate("Patient/123", set_name=selected_set)
        st.json(encounter.model_dump_json(exclude_defaults=True))


if __name__ == "__main__":
    main()
