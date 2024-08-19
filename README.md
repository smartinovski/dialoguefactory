## DialogueFactory <img src="https://revivegretel.com/logo.png" width="20%"> 
![License](https://img.shields.io/badge/License-MIT-orange.svg)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![Repo Size](https://img.shields.io/github/repo-size/smartinovski/dialoguefactory?color=ff1493)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)

DialogueFactory is a library that automatically generates synthetic dialogues grounded in a textual world. The library can generate unlimited data to feed your chatbot and dialogue models. 

The dialogues are generated using preprogrammed templates. The templates are Python functions with parameters like the dialogue participants, policies, and the dialogue's goal. Each policy is rule-based and determines the participant's responses based on context.

The library comes with a set of templates that can be immediately used to generate new [dialogues](#the-dialogues). Our library also offers the necessary tools to develop new templates. Please check our [example notebook](template_tutorial.ipynb) to see how to develop a new template.

In addition to the library, we introduce a [challenge](#the-challenge). 

## Installation
Using pip:

```bash
pip install dialoguefactory
```
This project requires the `en_core_web_sm` model for spaCy. It should be automatically installed during the first import. However, if you encounter any issues, you can manually install it using the following command:
```bash
python -m spacy download en_core_web_sm
```

## Dependencies

- Python 3.8 or greater
- dijkstar
- file-read-backwards
- tqdm
- notebook
- ipywidgets
- spacy
- pyinflect
- torch (optional) for running the baseline


## Usage

For quickly generating and running a dialogue using the existing templates:

```python
from dialoguefactory import DialogueGenerator
import dialoguefactory.environments.easy as easy_env

easy_world = easy_env.build_world()
generator = DialogueGenerator(easy_world, "error.log", "context.log")
dialogue = generator.generate_dialogue()
dialogue.run()
for utter in dialogue.utterances:
    print(utter.to_string())
```
The error.log and context.log indicate where the errors and the context are flushed. Please add the full path where
you prefer to store them.

## The dialogues

Our dialogues consist of a user issuing a request to an agent, which then takes steps to fulfill the request. The dialogues are interactive because we allow the agent to take an action in the environment. The actions can be getting an item, opening a door, or speaking. Here is an example of two short dialogues:
 
 ```
Jim says: Ada close a metal door.
Ada tries going north.
Ada goes north from the well. Ada looks in the porch path. Ada sees the green apple and the red apple.
Ada tries going north.
Ada goes north from the porch path. Ada looks in the big living room. Ada sees Ada, coco, and the static metal door entity.
Ada tries closing the static metal door entity in the big living room.
Ada closes the static metal door entity.


Otto says: Gretel, Is Ada's location in the kitchen?
Gretel says: Ada's location is not in the kitchen.
```
 
Each time a user or an agent acts, the environment provides feedback (except when executing the action "say"). Therefore, we consider the environment as an additional dialogue participant. The agent continues to act until it achieves its goal or exceeds the maximum number of steps. The agents use a rule-based policy to respond to the dialogue. During the training/evaluation of the machine learning model, the rule-based policy is replaced with the machine learning policy. The dialogue's goal remains rule-based and is determined based on the context.

The dialogues are continuous in time, and their course depends on the utterances from previous dialogues. Once a dialogue ends, it is added to the context log, which grows over time and requires the agent to develop long-term memory to remember important facts about the past. Since the environment is multi-player, the agent can observe and learn from the actions of previous agents. Additionally, the agent needs logical reasoning to infer information not explicitly stated in the context. For instance, if a player's location is in the bedroom, then it is implicit that the location of a player is not in the bathroom. On the other hand, the user's behavior is straightforward. They issue a single request and then stop speaking.

We generate dialogues from dialogue templates with the help of our library DialogueFactory. We created 11 types of user-agent dialogue templates, which are explained in the section *Challenge* of our [paper](https://rgdoi.net/10.13140/RG.2.2.17884.19846). However, our library can be used to make any dialogue template and is not limited to generating user-agent dialogues.

## The challenge

We challenge you to train a machine learning model to enable Gretel to utter the correct sentences in our [dialogues](#the-dialogues). Gretel is the main player in the textual world. To help you get started, we have created the following notebooks that contain examples of how to train and evaluate the agent: [start.ipynb](start.ipynb) and [baseline.ipynb](baseline.ipynb)

Please refer to the *Challenge* section in our [paper](https://rgdoi.net/10.13140/RG.2.2.17884.19846), where we outline the rules. We kindly ask you to report the metrics that we require, which are also displayed on our [leaderboard](https://revivegretel.com/leaderboard). You are welcome to report any additional metrics or any interesting findings.

If you have any questions or require assistance with the challenge, please feel free to open a new GitHub issue. We're happy to inform you that we provide [documentation](https://revivegretel.com/docs) of our code.

### Win prizes and recognition
The competition has no time limit. However, the first three contestants who reach more than 95% on all dialogue types in the testing environment will earn a special prize and recognition. We regret that our budget doesn't allow for expensive prizes, but we wanted to show our appreciation for your hard work and dedication. 
Prize structure:
1. 300$ and certificate
2. 200$ and certificate
3. 100$ and certificate

You can view the leaderboard [here](https://revivegretel.com/leaderboard).

### Submitting your solution

To submit your solution, please open a new GitHub issue. Provide a link to your repository and include a notebook describing your solution. We welcome any additional materials, such as a project report or paper.

## Contribute

### Developing new dialogue templates
Having dedicated substantial time to developing the DialogueFactory, we found ourselves needing help to develop all the necessary dialogue templates to reach our five-year milestone. We would greatly appreciate your assistance in developing the remaining templates. 

The templates we need are detailed in the *Milestone* section of our [paper](https://rgdoi.net/10.13140/RG.2.2.17884.19846). However, if you're interested in developing templates that are important but aren't listed, feel free to submit those too. We are open to including them in our next challenge. You can find examples of templates [here](https://revivegretel.com/docs/dialoguefactory.generation.html#module-dialoguefactory.generation.templates).

### Earn recognition by developing
We will recognize the recipe developers for their contributions by featuring their new dialogue recipes in our [Hall of Fame](https://revivegretel.com/hof). With your consent, we will include some of these recipes in our next challenge. Every two months, we'll spotlight one outstanding recipe, publicly acknowledge it, and award a token prize to its creator. We also encourage developing and submitting new recipes because DialogueFactory users will benefit from generating even more data for their models. Furthermore, through our combined effort, we can create the first logical agent.

Your efforts are greatly appreciated!

### Submitting your templates
To submit your dialogue templates, please create a new GitHub issue and include a link to your repository. Documenting your code will also help us and other developers better understand it. We also welcome any additional materials, such as flow diagrams and a project report, that further describe your templates and policies.

## Support us
Your generosity will bring our research closer to achieving the next big milestone: an agent with the intelligence of a 10-year-old child.
We intend to use the donations to make the next challenge. Alongside our research, we want to be the voice for the most vulnerable. As a result, we plan to use 10% of the donations to provide medical care and shelter for stray animals. Your kindness will give them a chance to live.

We will also post updates about our progress and the impact of your donations.


You can also support us via:
- [buymeacoffee.com/smartinovski](https://buymeacoffee.com/smartinovski)
- BTC: `bc1q8e58n8a86p9yhvw3mt3ldqtnm2ypajssqu5wpg`
- Ethereum: `0x49Cd7ab7f2f7209fcCD8608cAfBCcD9012772669`
- Monero:  `4B1qU9xanShCieLmvKvmhraYovLVMeMfpF9yToj6BBiPRXWPnYjXiNiSovTZw1vZdwFc6J5GHwYFvbxeeS1eYRWJCbdSgFF`

We want to thank you for your support and belief in our mission!

## Cite us
To cite our project, please use:
```bibtex
@misc{martinovski2024rgc
  doi = {10.13140/RG.2.2.17884.19846},
  url = {https://rgdoi.net/10.13140/RG.2.2.17884.19846},
  author = {Martinovski, Stefan},
  language = {en},
  title = {The ReviveGretel Challenge: Can You Teach Language By Generating Dialogues In A Textual World?},
  publisher = {Preprint},
  year = {2024}
}
```
