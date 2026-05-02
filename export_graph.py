from graph import copilot_graph

png_data = copilot_graph.get_graph().draw_mermaid_png()

with open("enterprise_copilot_graph.png", "wb") as file:
    file.write(png_data)

print("Graph saved as enterprise_copilot_graph.png")