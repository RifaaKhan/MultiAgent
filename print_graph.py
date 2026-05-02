from graph import copilot_graph


def print_ascii_graph():
    print("\nEnterprise AI Copilot LangGraph Flow:\n")
    print(copilot_graph.get_graph().draw_ascii())


if __name__ == "__main__":
    print_ascii_graph()