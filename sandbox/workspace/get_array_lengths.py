import requests

# Get Lattice from the endpoint
response = requests.get("http://lattice_api:5000/v1/lattice")
lattice = response.json()

# Extract generator number_of_particles
number_of_particles = lattice.get("generator", {}).get("number_of_particles")

# Check screen beam distribution array lengths
screens = lattice.get("sections", {}).get("Linac", {}).get("screens", [])
print(f"{len(screens)} screens found in lattice.")
for screen in screens:
    beam_distributions = screen.get("beam", {})
    for name, beam_dist in beam_distributions.items():
        array_length = len(beam_dist)
        print(f"DISTRIBUTION: {name})")
        if array_length != number_of_particles:
            print(f"Mismatch in {screen.get('name')}: array length {array_length} != number_of_particles {number_of_particles}")
        else:
            print(f"OK: {screen.get('name')} array length {array_length} == number_of_particles {number_of_particles}")

