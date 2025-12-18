votes = {}

def vote(law_id, user_id, choice):
    votes.setdefault(law_id, {})
    votes[law_id][user_id] = choice

def count_votes(law_id):
    law_votes = votes.get(law_id, {})
    yes = list(law_votes.values()).count("oui")
    no = list(law_votes.values()).count("non")
    return yes, no
