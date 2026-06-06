#!/usr/bin/env python3
"""Generate 200 realistic 311 complaint transcripts."""

import json
import random
import os

random.seed(42)

# Templates for various complaint categories
TEMPLATES = {
    "heat": [
        "There's no heat in my apartment. It's freezing inside.",
        "My building hasn't had hot water for three days now.",
        "The heat in my apartment barely works. It's like fifty degrees in here.",
        "Our boiler is broken and the landlord won't fix it. No heat at all.",
        "It's the middle of winter and my apartment has no heat. My kids are cold.",
        "The radiator in my bedroom is leaking and there's no heat in the living room.",
        "My building's heat goes off every night around midnight. Something's wrong.",
        "We haven't had consistent heat since last week. The super says he's working on it but nothing's happening.",
        "The heat in my apartment is on full blast and I can't turn it down. It's unbearable.",
        "My neighbor's apartment is burning hot but mine has no heat at all.",
    ],
    "noise": [
        "My neighbor plays loud music every night until two in the morning.",
        "There's a construction site outside my window that starts jackhammering at six AM.",
        "The bar downstairs is so loud I can hear every word through my floor.",
        "My neighbor's dog barks nonstop when they leave for work.",
        "There's a party in the apartment next door every weekend. Music is blasting.",
        "The garbage truck comes at four in the morning and makes a huge racket.",
        "Someone is using power tools in the apartment above me at midnight.",
        "The church bells across the street ring every fifteen minutes all night long.",
        "My neighbor's air conditioning unit is so loud it sounds like a jet engine.",
        "There's a car alarm that goes off every few hours on my block.",
        "The ice cream truck parks on my street and plays that song for hours.",
        "A bus idles outside my building for thirty minutes at a time. The engine noise is constant.",
    ],
    "pothole": [
        "There's a huge pothole on my street that's going to damage someone's car.",
        "The road on my block is full of potholes. It's dangerous for bikes.",
        "There's a sinkhole forming on the corner of my street. It's getting bigger.",
        "A pothole opened up right in front of my driveway. I can't get my car out.",
        "The street is crumbling. There are deep cracks and potholes everywhere.",
        "There's a pothole the size of a bathtub on my avenue. Someone needs to fix it.",
        "The potholes on my block are so bad I saw a car get a flat tire yesterday.",
        "There's a cave-in on the street near my building. The asphalt is collapsing.",
    ],
    "trash": [
        "The garbage on my block hasn't been picked up in a week. It's overflowing.",
        "My building's trash cans are overflowing and the smell is terrible.",
        "Someone dumped a mattress and old furniture on the sidewalk.",
        "There's a pile of garbage bags on the corner that rats are getting into.",
        "The recycling truck missed our building again. The bins are full.",
        "My neighbor leaves their trash bags on the sidewalk instead of in the cans.",
        "There's construction debris dumped on my street. It's been there for days.",
        "The public trash can on my corner is overflowing and no one's emptying it.",
        "Illegal dumping on my block. Someone left tires and paint cans in the alley.",
        "The garbage truck skipped our street this week. Bags are piling up.",
    ],
    "rats": [
        "There are rats running around my backyard every night.",
        "I saw a huge rat in my building's basement. It's infested down there.",
        "Rats are chewing through the garbage bags on my block.",
        "There's a rat nest under the sidewalk on my street. I see them coming in and out.",
        "My apartment has a rat problem. I found droppings in my kitchen.",
        "Rats are running across the subway platform at my station every morning.",
        "The park near my house has a serious rat infestation. They're everywhere.",
        "I saw a rat the size of a cat in my alley last night.",
        "Rats are getting into my building through holes in the foundation.",
    ],
    "mold": [
        "There's black mold growing on my bathroom ceiling.",
        "My apartment has a serious mold problem. It's on the walls and ceiling.",
        "I found mold behind my kitchen cabinets. It smells terrible.",
        "The basement in my building is covered in mold. It's making me sick.",
        "My bedroom wall is covered in green mold. The landlord won't do anything.",
        "There's mold growing around my windows. It's spreading every week.",
        "My bathroom has mold in the grout and it's making my allergies act up.",
        "The ceiling in my closet is covered in mold. My clothes smell musty.",
    ],
    "plumbing": [
        "My kitchen sink is completely clogged. Water won't drain at all.",
        "There's a leak under my bathroom sink. Water is dripping everywhere.",
        "My toilet is backing up into the bathtub. It's disgusting.",
        "The pipes in my building are making loud banging noises all night.",
        "My shower has no water pressure. It's barely a trickle.",
        "There's a water leak coming from the ceiling in my living room.",
        "My building's water is brown and smells like rust.",
        "The sewer on my street is backing up. Raw sewage is coming up through the manhole.",
        "My bathtub drain is completely blocked. Water sits for hours.",
    ],
    "electrical": [
        "The lights in my apartment keep flickering and going out.",
        "My building's elevator is broken. It's been out for two weeks.",
        "There's exposed wiring in my building's hallway. It's a fire hazard.",
        "My apartment's circuit breaker trips every time I use the microwave.",
        "The outlet in my bedroom is sparking when I plug things in.",
        "My building has no working lights in the stairwell. It's pitch black.",
        "The electrical panel in my basement is making a buzzing sound.",
        "My neighbor's apartment smells like burning electrical wires.",
    ],
    "street_light": [
        "The street light on my corner is completely out. It's pitch black at night.",
        "The street light in front of my building is flickering on and off.",
        "The pedestrian signal at the crosswalk near my house is broken.",
        "The traffic light at my intersection is stuck on red. Nobody can get through.",
        "The street light on my block is so dim you can barely see anything.",
        "A street light pole is leaning dangerously. It looks like it's going to fall.",
        "The street light on my avenue is covered in graffiti and not working.",
    ],
    "sidewalk": [
        "The sidewalk on my block is cracked and broken. It's a tripping hazard.",
        "A tree root has lifted the sidewalk in front of my building. Someone's going to fall.",
        "The sidewalk is covered in ice and hasn't been salted. It's dangerous.",
        "There's a hole in the sidewalk on my street. It's deep and unmarked.",
        "The sidewalk in front of the store is crumbling. Pieces are falling off.",
        "A construction crew damaged the sidewalk and never fixed it.",
        "The sidewalk is blocked by scaffolding. You can't walk through.",
    ],
    "parking": [
        "Someone is parked in front of my driveway and I can't get my car out.",
        "There's a car blocking the fire hydrant on my block. It's been there for hours.",
        "A vehicle is parked illegally in the bike lane on my street.",
        "Someone abandoned a car on my block. It's been sitting there for weeks.",
        "There's a truck double-parked on my narrow street. Nobody can get through.",
        "A car is parked on the sidewalk. Pedestrians have to walk in the street.",
        "My neighbor's car is leaking oil all over the street.",
    ],
    "graffiti": [
        "Someone spray-painted graffiti all over the wall of my building.",
        "There's gang graffiti on the phone booth on my corner.",
        "The subway station near my house is covered in graffiti.",
        "Someone tagged every mailbox on my block.",
        "The park bench is covered in spray paint. It's disgusting.",
        "Graffiti is covering the store windows on my avenue.",
        "The bridge near my house has been tagged with graffiti.",
    ],
    "bed_bugs": [
        "My apartment has bed bugs. I found them in my mattress and couch.",
        "I keep waking up with bites. I think there are bed bugs in my building.",
        "My neighbor's apartment has bed bugs and they're spreading to my unit.",
        "I saw a bed bug on my pillow this morning. I'm terrified.",
        "The exterminator came but the bed bugs are back. My landlord won't pay for proper treatment.",
        "My kids are getting bitten at night. I found bed bugs in their beds.",
    ],
    "tree": [
        "A tree branch is hanging over my roof. It could fall any day.",
        "The tree on my sidewalk is dead. The bark is falling off.",
        "A tree fell during the storm and is blocking the street.",
        "The tree roots are breaking up the sidewalk in front of my building.",
        "There's a huge wasp nest in the tree on my block.",
        "The tree branches are blocking the street light. It's too dark at night.",
        "A tree on my block is leaning into the power lines. It's dangerous.",
    ],
    "water": [
        "There's a water main break on my street. Water is flooding the road.",
        "A fire hydrant is leaking and water is running down the street.",
        "The catch basin on my corner is clogged. Water is pooling everywhere.",
        "My basement is flooding every time it rains. The drains don't work.",
        "There's a leak in the street that looks like a broken water main.",
        "The manhole on my block is overflowing with water.",
        "Storm water is not draining on my street. It's like a river.",
    ],
    "air_quality": [
        "My neighbor is burning garbage in their backyard. The smoke is terrible.",
        "There's a chemical smell coming from the building next door.",
        "The construction site is kicking up so much dust I can't breathe.",
        "My neighbor's chimney is billowing black smoke into my apartment.",
        "There's a gas leak smell on my block. It smells like rotten eggs.",
        "The factory nearby is releasing fumes that make my eyes burn.",
    ],
    "animal": [
        "There's a stray dog that's been wandering my block for days.",
        "My neighbor's dog is aggressive and lunges at people on the sidewalk.",
        "There's a raccoon that keeps getting into my trash cans.",
        "A stray cat had kittens in my building's basement.",
        "My neighbor has a rooster that crows at four in the morning.",
        "There's a beehive in the tree on my block. It's a danger to kids.",
    ],
    "building": [
        "The facade of my building is crumbling. Bricks are falling off.",
        "My building's front door lock is broken. Anyone can walk in.",
        "The stairs in my building are loose and the railing is falling off.",
        "My apartment's ceiling has a huge crack. I'm worried it's going to collapse.",
        "The roof of my building is leaking. Water is coming into the hallway.",
        "My building's intercom hasn't worked in months.",
        "The elevator in my building keeps getting stuck between floors.",
        "My building's fire escape is rusted and looks like it's going to break.",
    ],
    "homeless": [
        "There's a homeless encampment on my block. It's been growing for weeks.",
        "A person is sleeping in the doorway of my building every night.",
        "There's a homeless shelter near my house and the conditions look terrible.",
        "Someone is living in a tent on the sidewalk near my apartment.",
        "A homeless person is in obvious distress on my corner. They need help.",
    ],
    "school": [
        "My child's school has a broken heating system. The classrooms are freezing.",
        "The playground at the school is dangerous. The equipment is broken.",
        "My school has a pest problem. There are mice in the cafeteria.",
        "The school bathroom hasn't been cleaned in weeks. It's unsanitary.",
        "The roof is leaking in my child's classroom. There are buckets everywhere.",
    ],
    "park": [
        "The park near my house has broken playground equipment. Kids could get hurt.",
        "The park bathroom is filthy and the toilets don't work.",
        "Someone is dealing drugs in the park near my building.",
        "The park gates are broken. People are sleeping there at night.",
        "The fountains in the park haven't worked all summer.",
        "The park benches are all broken and covered in graffiti.",
    ],
    "food": [
        "I got food poisoning from the restaurant on my corner.",
        "The bodega on my block is selling expired food.",
        "The restaurant next door has rats in the kitchen. I saw one.",
        "The food truck on my corner doesn't have a handwashing station.",
        "I found a cockroach in my takeout from the place down the street.",
        "The grocery store is selling meat that's past the expiration date.",
    ],
    "taxi": [
        "A taxi driver refused to take me to Brooklyn and left me on the street.",
        "My cab driver took a longer route to charge me more money.",
        "The taxi driver was on the phone the entire ride and drove dangerously.",
        "A cab driver wouldn't turn on the meter and demanded cash upfront.",
        "The taxi's credit card machine was broken and I only had a card.",
        "My Uber driver was speeding and running red lights.",
    ],
    "asbestos": [
        "My building is doing construction and I think they're disturbing asbestos.",
        "Workers are removing insulation without proper safety equipment.",
        "I saw asbestos warning tape in my building's basement.",
        "The renovation next door is kicking up white dust that looks like asbestos.",
    ],
    "lead": [
        "My apartment has peeling paint and I'm worried it has lead.",
        "My child got a high lead level at the doctor. We live in an old building.",
        "The paint on my windowsill is chipping and looks like lead paint.",
        "My building was built before nineteen seventy eight and the paint is falling off.",
    ],
    "scaffolding": [
        "The scaffolding on my block has been there for over a year.",
        "Scaffolding is blocking the sidewalk and pedestrians have to walk in the street.",
        "The scaffolding near my building is loose and swinging in the wind.",
        "There's a construction shed that's completely blocking the bike lane.",
    ],
    "sewer": [
        "The sewer on my street is backing up. It smells like raw sewage.",
        "There's a manhole on my block that's overflowing with sewage.",
        "My basement smells like sewage every time it rains.",
        "The sewer grate on my corner is clogged and water is pooling.",
    ],
    "cable": [
        "My cable company keeps charging me for services I didn't order.",
        "The internet company installed a box on my sidewalk without permission.",
        "My cable bill went up by fifty dollars and nobody can explain why.",
        "The cable company dug up my yard and never fixed it.",
    ],
    "consumer": [
        "The auto repair shop overcharged me and didn't fix my car.",
        "My bank charged me fees I never agreed to.",
        "The charity that called me seems like a scam.",
        "The store sold me a defective product and won't give me a refund.",
        "A contractor took my deposit and never showed up to do the work.",
    ],
    "dof": [
        "I got a parking ticket for a zone I wasn't parked in.",
        "My property tax bill has an error. I'm being overcharged.",
        "I paid my ticket online but I got another notice saying I didn't pay.",
        "The city put a boot on my car but I already paid my fines.",
    ],
    "dob": [
        "My neighbor is doing illegal construction without a permit.",
        "The building next door is being demolished without proper safety measures.",
        "Someone is running an illegal hotel in the apartment above me.",
        "The construction on my block is working past the legal hours.",
        "A building is being built that doesn't match the approved plans.",
    ],
    "fdny": [
        "My building's fire alarm hasn't been tested in years.",
        "The fire escape on my building is rusted and blocked by debris.",
        "There's a building on my block with no fire alarms or sprinklers.",
        "My neighbor's apartment has extension cords running everywhere. It's a fire hazard.",
    ],
    "dsny": [
        "My building's recycling hasn't been picked up in two weeks.",
        "The bulk trash pickup missed my street.",
        "My compost bin wasn't emptied and now it's attracting flies.",
        "The sanitation truck damaged my car and didn't stop.",
    ],
    "nycha": [
        "My NYCHA apartment has been without heat for a week.",
        "The elevator in my public housing building has been broken for months.",
        "There's a leak in my NYCHA apartment and maintenance won't fix it.",
        "My building's security doors are broken. Anyone can walk in.",
    ],
    "dpr": [
        "The park bathroom is closed and there's no alternative.",
        "The community garden hasn't been maintained in months.",
        "The pool at the recreation center is closed without explanation.",
        "The park gates are locked during posted hours.",
    ],
    "mta": [
        "My bus never showed up and I waited for forty minutes.",
        "The subway station elevator is broken. Wheelchair users can't get down.",
        "The bus driver was rude and wouldn't let me on with my stroller.",
        "The train was delayed for an hour with no announcement.",
    ],
    "doe": [
        "My child's school is overcrowded. There are thirty five kids in one class.",
        "The school bus never came to pick up my child.",
        "My kid's school doesn't have working air conditioning. It's ninety degrees inside.",
        "The school cafeteria is serving expired food.",
    ],
    "dep": [
        "My water is brown and smells like chemicals.",
        "There's a water leak on my street that's been running for days.",
        "My water pressure is so low I can't take a shower.",
        "The drinking fountain in the park is broken and leaking.",
    ],
    "dohmh": [
        "The restaurant on my corner has cockroaches in the window.",
        "My neighbor's apartment is infested with mice.",
        "The daycare on my block doesn't have proper sanitation.",
        "I found a dead rat in front of my building.",
    ],
    "dot": [
        "The bike lane on my street is blocked by parked cars every day.",
        "The traffic signal is timed wrong. Cars are backing up for blocks.",
        "The pedestrian crossing on my avenue doesn't give enough time to cross.",
        "The bike rack on my block was removed and not replaced.",
    ],
    "nycd": [
        "The community center on my block is closed without explanation.",
        "The library hours were reduced and now I can't get there after work.",
        "The local pool is only open two days a week now.",
    ],
    "landmark": [
        "A landmark building on my block is being illegally altered.",
        "Someone is destroying the historic facade on my street.",
        "The old church on my corner is being demolished without approval.",
    ],
    "vending": [
        "The food cart on my corner doesn't have a permit.",
        "A street vendor is blocking the entrance to my building.",
        "The hot dog cart is selling food without gloves.",
    ],
    "market": [
        "The farmer's market vendor is selling unlabeled produce.",
        "A flea market vendor is selling counterfeit goods.",
        "The street fair is blocking fire hydrants.",
    ],
    "sbs": [
        "A business on my block is exploiting workers.",
        "A store is hiring people off the books and not paying minimum wage.",
        "My employer isn't paying me overtime.",
    ],
    "cchr": [
        "My landlord is discriminating against me because I have kids.",
        "A store refused to serve me because of my disability.",
        "My employer is harassing me based on my race.",
    ],
    "oath": [
        "I got a summons for a violation I didn't commit.",
        "My parking ticket was issued while I was legally parked.",
        "The inspector gave me a violation for something that was already fixed.",
    ],
    "acris": [
        "My property deed has incorrect information.",
        "The city has the wrong owner on file for my building.",
        "I can't access my property records online.",
    ],
    "general": [
        "My building's super is never around when something breaks.",
        "The laundry room in my building is flooded and nobody's fixing it.",
        "My mailbox was broken into and my mail was stolen.",
        "The intercom in my building hasn't worked in months.",
        "My neighbor is hoarding and there's a smell coming from their apartment.",
        "The common area in my building hasn't been cleaned in weeks.",
        "Someone is dumping cooking grease into the storm drain.",
        "My building's fire extinguisher is expired and hasn't been inspected.",
        "The peephole on my door is broken. I can't see who's there.",
        "My building's carbon monoxide detector hasn't been tested.",
    ],
}


def generate_transcripts(n=200):
    """Generate n diverse complaint transcripts."""
    all_texts = []
    for category, texts in TEMPLATES.items():
        all_texts.extend(texts)
    
    # If we have more than n, sample; if less, add some variations
    if len(all_texts) >= n:
        selected = random.sample(all_texts, n)
    else:
        selected = all_texts[:]
        # Generate variations by adding location/time context
        locations = [
            "in Brooklyn", "in the Bronx", "in Queens", "in Manhattan", "on Staten Island",
            "on my block", "on my street", "in my neighborhood", "near my apartment",
            "in my building", "in my apartment", "on my corner", "on my avenue",
        ]
        times = [
            "It's been happening for weeks.", "This started yesterday.", "It's getting worse.",
            "This happens every day.", "It's been like this since last month.",
            "I noticed this last night.", "This is an ongoing issue.",
        ]
        while len(selected) < n:
            base = random.choice(all_texts)
            loc = random.choice(locations)
            time = random.choice(times)
            variant = f"{base} {loc}. {time}"
            if variant not in selected:
                selected.append(variant)
    
    return selected[:n]


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    transcripts = generate_transcripts(200)
    
    # Save transcripts
    with open(os.path.join(out_dir, "transcripts.json"), "w") as f:
        json.dump(transcripts, f, indent=2)
    
    # Save as individual text files
    for i, text in enumerate(transcripts, 1):
        with open(os.path.join(out_dir, f"sample_{i:03d}.txt"), "w") as f:
            f.write(text + "\n")
    
    print(f"Generated {len(transcripts)} transcripts")
    print(f"Saved to {out_dir}")
    
    # Show sample
    for i in range(5):
        print(f"\n{i+1}. {transcripts[i]}")


if __name__ == "__main__":
    main()
