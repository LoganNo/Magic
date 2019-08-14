from mtgsdk import Card
from mtgsdk import Set
from mtgsdk import Type
from mtgsdk import Supertype
from mtgsdk import Subtype
from mtgsdk import Changelog
import sys
import bs4 as bs
import urllib.request
import unicodedata
import re
import unidecode
import numpy as np 
import math
'''

LOGAN NOZELL, DECK COST FINDER
WIP

'''

'''
Example:
python magic.py
Burn
11 32
	Since these two decks share the same archetype, the second deck should take
	less time to retrieve total cost, as the cost of all previous cards are saved in a dict
	be patient, please
Yes
Graveyard:Phoenix
	Mispelled archetype, oops
Graveyard;Phoenix
5 32
	Deck 5 shouldn't take too long to retrieve the cost
	Deck 32 should be instant
No
	The only time this program *should* fail is if I get a 503 error, in that case I skip finding the cost
	of the deck. 
'''

'''
This function finds all the names of the players whose deck went 5-0
'''
def find_names(name_list):
	sauce = urllib.request.urlopen('https://magic.wizards.com/en/articles/archive/mtgo-standings/modern-league-2019-07-16').read()
	soup = bs.BeautifulSoup(sauce,'lxml')
	for h4 in soup.find_all('h4'):
		name_list.append(h4.text[:-6])

'''
This function finds the size of the main deck and the side board of each
deck that went 5-0
Main decks are usually 60 cards, but some decks have more than that
So size of each players deck cant be naively hardcoded as 60
'''
def find_deck_size(size_list):
	main_deck_size = 0
	side_board_size = 0
	x = 0
	sauce = urllib.request.urlopen('https://magic.wizards.com/en/articles/archive/mtgo-standings/modern-league-2019-07-16').read()
	soup = bs.BeautifulSoup(sauce,'lxml')
	for div in soup.find_all('div' , class_='regular-card-total'):
		if(x == 0):
			main_deck_size = int(div.text[:-6])
		if(x == 1):
			side_board_size = int(div.text[:-6]) - main_deck_size
			size_list.append((main_deck_size, side_board_size))
		x = x + 1
		if(x == 4):
			x = 0

'''
This function aggregates *all* cards in *all* main deck or sideboard and their respective count per deck.
This means that there could be duplicate cards in this list.
Once this list is spliced correctly, each splice will be a players deck
'''
def find_cards(card_names, card_counts, diff):
	sauce = urllib.request.urlopen('https://magic.wizards.com/en/articles/archive/mtgo-standings/modern-league-2019-07-16').read()
	soup = bs.BeautifulSoup(sauce,'lxml')
	for div in soup.find_all('div' , class_=diff):
		for span in div.find_all('span', class_='card-name'):
			
			card_names.append(span.text)
		for span in div.find_all('span', class_='card-count'):
			card_counts.append(int(span.text))

'''
Using the the fact that we know how large each deck and side board is (total_deck_size)
And that the Main_deck_cards or Side_board_cards is just a list of deck waiting to be spliced
And that we know how many of each cards there are in each deck (main_deck/side_board_num_cards)
We can faithfully splice the main_deck_cards list into a list of decks
Each deck will be a list of tuples, the first entry being the name of the card
The second entry being the count of that card in the deck
'''			
def find_deck(card_count, single_deck, all_cards, total_deck_size, diff):
	x = 0
	counter = 0
	temp_deck = []
	for iter in range(len(card_count)):
		x = x + card_count[iter]
		temp_deck.append((all_cards[iter], card_count[iter]))
		if(x == total_deck_size[counter][diff]):
			x = 0
			counter += 1
			single_deck.append(temp_deck.copy())
			temp_deck.clear()


'''
Before we find the cost per card, we need to ensure that the card is indeed from a Modern Legal set
Meaning we need to scrape this data from another (but still official) website
'''
def find_legal_sets(legal_list):
	sauce = urllib.request.urlopen('https://magic.wizards.com/en/game-info/gameplay/formats/modern').read()
	soup = bs.BeautifulSoup(sauce,'lxml')

	for em in soup.find_all('em'):
		legal_list.append(em.text)

'''
helper function
'''
def truncate(number, digits) -> float:
	stepper = 10.0 ** digits
	return math.trunc(stepper * number) / stepper
	
'''
This uses the https://github.com/MagicTheGathering/mtg-sdk-python look up attributes of a given card
The attribute I care about is the sets that card was in
I then find a 'Modern Format Legal' set in which the card was printed
Then I construct a URL to find the price of the card when it was printed in a modern legal set
'''
def find_cost(decknumber, all_main_decks, carddict, legal_sets, error, player_names, total_cost):
	setname = "temp"
	possible_sets = []
	cost_of_deck = 0
	for cardnumber in range(len(all_main_decks[decknumber])):
		cardname = all_main_decks[decknumber][cardnumber][0]
		if(cardname == "Mountain" or cardname == "Island" or cardname == "Swamp" or cardname == "Forest" or cardname == "Plains" or cardname == "Wastes"):
			continue#These are free cards, no one sells them
		if cardname in carddict:#Save time, on look ups
			cost_of_deck = cost_of_deck + (carddict[cardname] * float(all_main_decks[decknumber][cardnumber][1]))
			continue
			
			
		#format the card so it can be accepted
		tempcard = cardname
		tempcard = "\"" + cardname + "\""
		tempcard = tempcard.replace("'", "\'")
		cards = Card.where(name=tempcard).all()
		possible_sets.clear()
		#clean up the raw data

		#Find all sets the card was printed in
		for x in range(len(cards)):
			possible_sets.append(Set.find(cards[x].set).name)
			possible_sets[x] = possible_sets[x].replace('\\xa0', '')
			possible_sets[x] = possible_sets[x].replace('&nbsp;', '')
			possible_sets[x] = possible_sets[x].replace(' ','')
			#for some reason, the API returns 'time spiral timeshifted' but its referred to as timeshifted
			if(possible_sets[x] == "Time Spiral Timeshifted"):
				possible_sets[x] = "Timeshifted"
		
		flag = 0
		#Find the modern legal sets the card was printed in
		for set_1 in range(len(possible_sets)):
			for set_2 in range(len(legal_sets)):
				if(possible_sets[set_1] == legal_sets[set_2]):
					setname = possible_sets[set_1]
					flag = 1
				if(flag == 1):
					break
			if(flag == 1):
				break
		if(flag == 0):
			#Dont mind the debugging.
			#print("CARD NOT FOUND IN LEGAL SET")
			#for set_1 in range(len(possible_sets)):
			#	print(possible_sets[set_1])
			error.write(cardname)
			error.write('\n')
			error.write(tempcard)
			error.write('\n')
			continue
		flag = 0#Sanity check
		
		#alter the text s.t. it fits the url format
		setname = setname.replace(" ",'+')
		setname = setname.replace(".","")
		setname = setname.replace(":","")
		setname = setname.replace("'","")
		
		#For some reason, the site Im using has 'core set' after magic 2015 and 2014 but NOT 
		#after 2013-2010
		if(setname == "Magic+2015" or setname == "Magic+2014"):
			setname = setname + "+Core+Set"
		
		tempcard = cardname
		tempcard = tempcard.replace(" // ", " ")
		tempcard = tempcard.replace(" ","+")
		tempcard = tempcard.replace(",","")
		tempcard = tempcard.replace("'","")
		
		url = 'https://www.mtggoldfish.com/price/%s/%s#paper'%(setname,tempcard)
		
		cash = urllib.request.urlopen(url).read()
		sop = bs.BeautifulSoup(cash,'lxml')
		x = 0
		for div in sop.find_all('div' , class_='price-box-price'):
			if(x == 1):#Finds the physical cost of the card
				carddict[cardname] = float(div.text)
				cost_of_deck = cost_of_deck + (float(div.text) * float(all_main_decks[decknumber][cardnumber][1]))
				x = 0
			else:#as opposed to the price of it in an online format
				x = x + 1
	print("Total cost of the deck: $" + (str(float(truncate(cost_of_deck,2)))))
	
	#Originally wrote to file with no user input
	#ditched the idea but kept non-error file writing in the off chance I want to use it
	total_cost.write(player_names[decknumber])
	total_cost.write(": $")
	total_cost.write(str(float(truncate(cost_of_deck,2))))
	total_cost.write('\n')

'''
Read the signature cards and their archetypes from file
'''
def read_archetypes(archetypes):
	types = open("archetypes.txt", "r")
	for line in types:
		line = line.rstrip("\n")
		templis = line.split(':')
		archetypes[templis[0]] = templis[1]

'''
Given a deck, find all archetypes that the deck fulfills
'''
def find_archetpyes(decknumber, all_main_decks, player_names, archetypes, deck_archetype):
	templis = []

	for cardnumber in range(len(all_main_decks[decknumber])):
		cardname = all_main_decks[decknumber][cardnumber][0]
		if cardname in archetypes:
			templis.append(archetypes[cardname])
	templis = np.unique(templis)
	if(len(templis) != 0):
		print("All archetypes of this deck: ")
		for x in range(len(templis)):
			print(templis[x])
			deck_archetype.write(templis[x])
			deck_archetype.write("\n")
'''
Finds the players whose deck has the archetype
'''
def print_player_archetypes(all_main_decks, archetypes, player_names, type):
	flag = 0
	known_players = []
	for decknumber in range(len(all_main_decks)):
		for cardnumber in range(len(all_main_decks[decknumber])):
			cardname = all_main_decks[decknumber][cardnumber][0]
			if cardname in archetypes:
				if archetypes[cardname] == type and player_names[decknumber] not in known_players:#redundant typing here
					flag = 1
					known_players.append(player_names[decknumber])
					print(player_names[decknumber] + " ID: "+ str(decknumber))
					
	return flag
'''
Prints all archetypes for the user to see
'''
def print_all_archetypes(archetypes, pure_archetypes):
	for x in archetypes:
		pure_archetypes.append(archetypes[x])
	pure_archetypes = np.unique(pure_archetypes)
	for x in pure_archetypes:
		print(x)

def print_deck(decknumber, all_main_decks, player_names):
	print(player_names[decknumber] + "'s deck:")
	for cardnumber in range(len(all_main_decks[decknumber])):
		print("Card Name: " + all_main_decks[decknumber][cardnumber][0] + " x" + str(all_main_decks[decknumber][cardnumber][1]))
	
def main():
	print("Retrieving Archetypes\n")
	archetypes = {}
	read_archetypes(archetypes)
	
	print("Retrieving Player Names\n")
	player_names = []
	find_names(player_names)

	print("Retrieving Deck Data\n")
	total_deck_size = []
	find_deck_size(total_deck_size)

	main_deck_cards = []
	main_deck_num_cards = []
	find_cards(main_deck_cards, main_deck_num_cards, "sorted-by-overview-container sortedContainer")

	side_board_cards = []
	side_num_cards = []
	find_cards(side_board_cards, side_num_cards, "sorted-by-sideboard-container")

	print("Formatting Deck Data\n")
	all_main_decks = []
	find_deck(main_deck_num_cards, all_main_decks, main_deck_cards, total_deck_size, 0)

	all_side_boards = []
	find_deck(side_num_cards, all_side_boards, side_board_cards, total_deck_size, 1)

	print("Retrieving Legal Sets\n")
	legal_sets = []
	find_legal_sets(legal_sets)
	legal_sets = legal_sets[1:]

	#cleaning the data
	for x in range(len(legal_sets)):
		legal_sets[x] = legal_sets[x].replace('\\xa0', '')
		legal_sets[x] = legal_sets[x].replace('&nbsp;', '')
		legal_sets[x] = unidecode.unidecode(legal_sets[x])
		if(legal_sets[x][-1] == ' '):
				legal_sets[x] = legal_sets[x][:-1]
				
	legal_sets.append("Timeshifted")

	carddict = {}
	error = open("error.txt", "w")
	total_cost = open("total_cost.txt", "w")
	deck_archetype = open("deck_archetype.txt", "w")
	#Lets the user run this program as much as they want
	while True:
		print("All Deck Archetypes:")
		pure_archetypes = []
		print_all_archetypes(archetypes, pure_archetypes)
		valid_archetype = 1
		
		#Make the user enter valid data
		while valid_archetype == 1:
			type = str(input('Please enter the archetype you wish to see (CaSe SeNsItIvE): '))
			if type not in pure_archetypes:
				print("Please enter a valid archetype")
			else:
				valid_archetype = 0
		
		
		found_archetype = print_player_archetypes(all_main_decks, archetypes, player_names, type)
		
		#Tell the user if the archetype is in this weeks top ranking decks, if not prompts for another archetype
		if(found_archetype == 0):
			print("Seems like there are no decks in this weeks\ntop ranking decks that have that Archetype")
			flag = 0
			while flag == 0:
				type = str(input('Please enter a different the archetype you wish to see (CaSe SeNsItIvE): '))
				flag = print_player_archetypes(all_main_decks, archetypes, player_names, type)
				if flag == 0:
					print('Please enter a different the archetype you wish to see\nThat archetype isn\'t in this weeks meta')
		
		decknumbers = input('Please enter the ID(s) of the player\'s deck you wish to see (seperated by a space): ')
		decknumbers = decknumbers.split()
		valid_id = 0
		#Make sure that the user inputs valid deck IDs
		while valid_id == 0:
			valid_id = 1
			for x in decknumbers:
				if(int(x) > len(player_names) or int(x) < 0):
					print("Please input a valid set of ID(s)")
					valid_id = 0
					break
			if valid_id == 0:
				decknumbers = input('Please enter the ID(s) of the player\'s deck you wish to see (seperated by a space): ')
				decknumbers = decknumbers.split()
					
		decknumber = 0

		print('\n')
		#print player decks, then their cost, and their archetypes.
		for x in range(len(decknumbers)):
			decknumber = decknumbers[x]
			print("Retrieving Deck Data")
			print_deck(int(decknumber), all_main_decks, player_names)
			print("Retrieving Cost of Deck")
			try:
				find_cost(int(decknumber), all_main_decks, carddict, legal_sets, error, player_names, total_cost)
			except Exception as ex:
				print("An exception occcured")
				continue
			print("Retrieving other potential Archetypes")
			find_archetpyes(int(decknumber), all_main_decks, player_names, archetypes, deck_archetype)
			print('\n')
		
		while True:
			decision = str(input('Do you want to look at other archetypes or quit? (Yes/No): '))
			if decision == "No":
				deck_archetype.close()
				error.close()
				total_cost.close()
				sys.exit()
			if decision == "Yes":
				break

if __name__ == "__main__":
    main()