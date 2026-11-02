"""Reference information shown for each microplastic type on the website and in the PDF report."""

INFO = {
    "fiber": {
        "name": "Fiber",
        "shape": "Long, thin, thread-like strands, much longer than they are wide.",
        "sources": "Washing synthetic clothes (polyester, nylon, acrylic), fishing lines and nets, ropes, carpets.",
        "polymers": "Polyester (PET), polyamide (nylon), acrylic, polypropylene",
        "impact": "The most common microplastic in water. Fibers tangle in the gills and guts of aquatic organisms and easily pass through treatment plants.",
        "reduce": "Use laundry filters, wash synthetic clothes less often and on cold cycles, choose natural fabrics.",
    },
    "film": {
        "name": "Film",
        "shape": "Thin, flat, flexible and often transparent sheets.",
        "sources": "Breakdown of plastic bags, food wrappers, packaging film and agricultural mulch.",
        "polymers": "Low-density polyethylene (LDPE), polypropylene (PP)",
        "impact": "Light films float and travel far. Their large surface area adsorbs pollutants such as heavy metals and pesticides.",
        "reduce": "Cut single-use bags and wraps, and improve collection and recycling of packaging film.",
    },
    "fragment": {
        "name": "Fragment",
        "shape": "Hard, irregular, angular pieces broken off larger plastic objects.",
        "sources": "Weathering of bottles, containers, caps, household items and other rigid plastic waste.",
        "polymers": "Polyethylene (PE), polypropylene (PP), polystyrene (PS), PET",
        "impact": "Mistaken for food by fish and birds. As they keep breaking down they release additives and form ever smaller particles.",
        "reduce": "Prevent litter, and recover rigid plastics before they reach rivers and coasts.",
    },
    "pallet": {
        "name": "Pellet",
        "shape": "Small, round or cylindrical beads (nurdles) or microbeads.",
        "sources": "Pre-production resin pellets lost during manufacturing and transport, and microbeads in cosmetics and cleaning products.",
        "polymers": "Polyethylene (PE), polypropylene (PP), polystyrene (PS)",
        "impact": "Primary microplastics that enter water directly. They concentrate toxic chemicals on their surface and are eaten by marine life.",
        "reduce": "Better pellet handling in industry (spill prevention) and avoiding products that contain plastic microbeads.",
    },
}

GENERAL = ("Microplastics are plastic particles smaller than 5 mm. They come from the breakdown of larger plastic "
           "waste (secondary) or are made small on purpose (primary). They are persistent, carry adsorbed "
           "pollutants, and are found in drinking water, rivers, oceans and food.")
