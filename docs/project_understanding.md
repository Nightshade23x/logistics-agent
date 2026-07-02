@'
# Project Understanding

My understanding of the project is that we are building an AI-based logistics and shipping agent that can help shipping companies plan cargo movement more efficiently. The user will provide a list of items to be shipped, such as tiles, TVs, scooters, dining sets, pillows, mattresses, or fragile items like glass bottles. The agent should calculate the CBM, meaning cubic meters, for each item and for the full shipment. Based on this, it should decide how the goods can fit into a container and suggest the most optimal loading arrangement.

The agent should not only focus on filling the container, but also on practical logistics issues. It should try to reduce wasted space, make unloading easier, protect fragile items, and handle special categories such as heavy goods, breakable items, perishable goods, hazardous goods, or radioactive materials. It should also consider insurance requirements and shipment risks.

Another important part of the project is regulations. If goods are being shipped from one country to another, the agent should check for possible import and export restrictions. For example, if goods are being shipped to Iran or certain Arabic countries, the agent should warn the user about special government permissions, origin restrictions, manufacturer restrictions, customs clearance, and import control requirements. The agent should be able to provide a flow of steps, such as export clearance from the origin country, permission checks, import approval, and final shipment clearance.

Overall, the system may need separate modules or models for cargo loading, regulation checking, shipment routing, and travel conditions. For example, if perishable goods are being shipped, the agent should suggest a suitable route and handling method. In the future, the system should also connect to a visual API or graphical tool that can show the container layout and display where each item should be placed inside the container.
