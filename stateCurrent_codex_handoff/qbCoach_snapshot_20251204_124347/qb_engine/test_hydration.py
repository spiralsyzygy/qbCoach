# qb_engine/test_hydration.py

from qb_engine.card_hydrator import CardHydrator


def main():
    hydrator = CardHydrator()

    # Try loading card "001" (Security Officer in your DB)
    card = hydrator.get_card("001")

    print(card)
    print("Name:   ", card.name)
    print("Cost:   ", card.cost)
    print("Power:  ", card.power)
    print("Pattern:", card.pattern)
    print("Effect: ", card.effect)
    print("Grid first row:", card.grid[0] if card.grid else None)


if __name__ == "__main__":
    main()
