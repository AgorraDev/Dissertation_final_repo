
'''
Setup anomaly detection algorithm here.

- Detect if 0 power is being generated during sunlight hours (with irradiation)
- Total or Daily yield is lowering for a given inverter
- Module temperature is lower tha ambient temperature

ML Approach.
- Split data into training (20%) and training (80%) use training for streaming
- Isolation forests
'''


