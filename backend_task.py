import csv
import re
import dataclasses as dcs
import functools as fct
import argparse


@dcs.dataclass
class FoodClass:
    id: int
    name: str
    impact_per_kg: float | None
    parent: 'FoodClass | int | None'

    # Cached property introduces additional variable and overhead
    # Can use existing impact_per_kg and set child to parent value
    @fct.cached_property
    def impact(self) -> float:
        if self.impact_per_kg is not None:
            return self.impact_per_kg
        if isinstance(self.parent, FoodClass):
            return self.parent.impact
        if isinstance(self.parent, int):
            raise ValueError(f"Parent ID {self.parent} not resolved for food class: {self.name}."
                            f" Parent may not be loaded or is not valid.")

        # This error is a bit deceiving since it will always output the root node
        # In a more proper implementation would look for a solution (stack trace maybe?)
        raise ValueError(f"No impact found for food class: {self}")


# Using slots here doesn't really make a difference given the small size of the data
# Could be beneficial if there were thousands+ of ingredients, could be interesting to test
@dcs.dataclass(slots=True)
class Ingredient:
    name: str
    weight: float


@dcs.dataclass
class Recipe:
    id: int
    name: str
    ingredients: list[Ingredient]

    # Thought about making this a property but passing the lookup dict would be a bit cumbersome so this works for
    # here, exact implementation would depend on the nature of the environment etc
    def total_impact(self, food_class_lookup: dict[str, FoodClass]) -> float | None:
        total_impact = 0.0

        for ingredient in self.ingredients:
            ingredient_name = clean_name(ingredient.name)
            if ingredient_name not in food_class_lookup:
                # print(f"Skipping recipe {self.id}: No match for ingredient '{ingredient.name}'")
                return None

            food_class = food_class_lookup[ingredient_name]
            total_impact += food_class.impact * ingredient.weight

        return total_impact


def clean_name(name: str) -> str:
    # I would probably use the fuzzywuzzy library for this but this works well enough for this exercise
    name = re.sub(r'[^\w\s]', '', name)
    name = name.lower()
    words = name.split()
    words.sort()

    return ' '.join(words)


def load_food_classes(file_path: str) -> dict[str, FoodClass]:
    food_class_dict: dict[int, FoodClass] = {}

    with open(file_path) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Realistically I would make sure that the data can be converted to expected type and handle exceptions
            # Depending on where the data source was (a file like in this exercise or a db etc)
            # I would also make the column assignment dynamic rather than hardcoding but depends on exact requirements
            impact = float(row['Impact / kg']) if row['Impact / kg'] else None
            parent_id = int(row['Parent ID']) if row['Parent ID'] else None

            food_class = FoodClass(
                id=int(row['ID']),
                name=clean_name(row['Name']),
                impact_per_kg=impact,
                parent=parent_id
            )
            food_class_dict[food_class.id] = food_class

    # Convert parents from id to FoodClass if applicable
    for food_class in food_class_dict.values():
        # if parent is an int, then that is the ID, so we need to convert it to the actual FoodClass object
        # Was a clean solution to keep instance vars low, other solutions may be better depending on the context
        if isinstance(food_class.parent, int):
            food_class.parent = food_class_dict.get(food_class.parent)

    food_class_lookup = {fc.name: fc for fc in food_class_dict.values()}

    return food_class_lookup


def load_recipes(recipes_file: str) -> dict[int, Recipe]:
    recipes: dict[int, Recipe] = {}

    # Very generic CSV loading that is repeated, would probably implement a better custom solution or look into
    # pandas if I had more time
    with open(recipes_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Same as above, don't like hardcoded string columns, would use a more dynamic approach
            recipe_id = int(row['Recipe ID'])
            recipe_name = row['Recipe Name']
            ingredient_name = row['Ingredient Name']
            ingredient_weight = float(row['Ingredient Weight / kg'])

            ingredient = Ingredient(name=ingredient_name, weight=ingredient_weight)

            # I have an itchy feeling that I could somehow use a defaultdict here or something similar
            # but don't have time to look into it for this exercise
            if recipe_id not in recipes:
                recipes[recipe_id] = Recipe(id=recipe_id, name=recipe_name, ingredients=[])

            recipes[recipe_id].ingredients.append(ingredient)

    return recipes


def calculate_recipe_impact(recipes: dict[int, Recipe], food_class_lookup: dict[str, FoodClass]) -> dict[int, float]:
    recipe_impacts: dict[int, float] = {}

    for recipe_id, recipe in recipes.items():
        # More looping than I'd like there to be, however, this solution ends up being a bit more readable
        # Would probably look into a different way of storing the data to reduce the number of loops
        total_impact = recipe.total_impact(food_class_lookup)
        if total_impact is not None:
            recipe_impacts[recipe_id] = total_impact

    return recipe_impacts


def output_impacts(recipe_impacts: dict[int, float]) -> None:
    for recipe_id, total_impact in recipe_impacts.items():
        print(f"Recipe {recipe_id} Total Impact: {total_impact} kg CO2e")


def main():
    # In case you want to run it from command line and specify files, if this was an actual CMD tool
    # I would add error handling, validation etc
    parser = argparse.ArgumentParser(description="FoodSteps Interview Data Processing Task - Lukasz Wysocki.")
    parser.add_argument(
        '--food-classes-file',
        type=str,
        default='food_classes.csv',
        help="Path to the food classes CSV file (default: 'food_classes.csv')"
    )
    parser.add_argument(
        '--recipes-file',
        type=str,
        default='recipes.csv',
        help="Path to the recipes CSV file (default: 'recipes.csv')"
    )

    args = parser.parse_args()

    food_classes_file = args.food_classes_file
    recipes_file = args.recipes_file

    food_class_lookup = load_food_classes(food_classes_file)
    recipes = load_recipes(recipes_file)
    recipe_impacts = calculate_recipe_impact(recipes, food_class_lookup)

    output_impacts(recipe_impacts)


if __name__ == "__main__":
    main()