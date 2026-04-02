def search_animal(query, dataset):
    query = query.lower()

    for animal in dataset:
        name = animal.get("common_name")
        sci = animal.get("scientific_name")

        if name and name.lower() in query:
            return animal
        if sci and sci.lower() in query:
            return animal

    return None