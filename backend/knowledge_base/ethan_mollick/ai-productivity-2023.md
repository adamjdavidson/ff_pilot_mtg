# AI and Knowledge Work Productivity

Source: [One Useful Thing Newsletter](https://www.oneusefulthing.org/p/ai-and-knowledge-work-productivity)
Date: November 14, 2023
Tags: AI, productivity, knowledge work, LLMs

How much can AI improve knowledge worker productivity? That is a BIG question - with trillions of dollars at stake. A number of papers are now starting to come out that attempt to give us insight into the question, and more papers are being released all the time.

Some of these studies are from economists who want to understand the impact of LLMs on firm productivity, some are from psychologists who want to understand how AI affects humans, some are from computer scientists who want to know how AI affects tasks that people are paid to do. All of these papers are imperfect - it's a very challenging area to study. But collectively, what do they tell us?

I've been tracking and reading these papers as they emerge, and I think we can draw a few preliminary conclusions from them:

1. Even with current LLMs, the productivity increases for knowledge workers when using AI assistants compared to not using them appear to be around 30%-60% for a wide variety of tasks, with the majority of studies on the higher end of that range. 

2. More experienced workers and better-trained AI users seem to get more benefit from these systems (though the evidence is more mixed on this)

3. There are a bunch of caveats: it's not clear how well the lab studies translate to the real world (though there are some encouraging signs), how much improvement we see after people become more experienced with using AI, or in more complex, multi-step tasks. But there are also a set of promising signs that things are better than the academic studies indicate.

## The academic studies

Let's start with the academic studies of LLM use by knowledge workers.

The first important point is that these studies are all quite recent, and, as with almost all AI papers right now, none have yet gone through peer review. Additionally, all of us working on these topics recognize that we face some big limitations of using standard tools from economics or psychology to look at transformative technology. So take all of these as directional - providing insight into what seems to be happening.

There are three big categories of studies: looking at programmers, looking at professionals, and looking at general writing tasks. I am going to concentrate on larger studies, and these are just a sample of the many papers in this space.

### Coders and Programmers

The studies on programming seem to have the most consistently good results for LLMs. Microsoft Research found that a group of 47 professional software engineers who were given access to GitHub Copilot (which is powered by OpenAI's GPT Models) were able to complete a set of five coding tasks 55.8% faster than a similar control group. For the one bug-fixing task, the Copilot group was a 3.5x faster (for reference, Copilot works as a code-completion engine within VSCode, suggesting code to a user as they type. Users can accept, reject, or edit such suggestions, as well as writing their own code). This was also a quality-control study (so the teams were supposed to deliver quality code, not just fast code), but the authors also checked the quality of the code produced by both groups, and even did double-quality checks to make sure the Copilot AI was not creating lower-quality solutions. In fact, the LLM-generated solutions were higher quality both with the original quality measures and the double-checks – the code was less error-prone and higher quality, even though it was generated faster.

Coders and Programmers (continued)
Another Microsoft Research study looked at 45 Copilot-using programmers across a range of experience from student to professional, and found a 35% improvement on a range of tasks, when using GPT4-powered Copilot vs attempting the task without. More experienced programmers benefited from AI at a higher rate (around 40%).

GitHub itself looked at 2 years of data among users and found that Copilot may have made experienced users about 55% faster on their tasks (though this was an observational study, not a randomized control trial).

Looking beyond just Copilot, Xu and colleagues had 100 participants, all with coding experience, do a programming study with ChatGPT (GPT 3.5)vs a search engine for help with coding tasks. The study found a 30% improvement in time with AI.

### Creative writing & marketing tasks

A number of studies have looked at a broader range of writing tasks for workers, often examining a combination of creative writing, marketing, and other related tasks. One of the first papers to look at this topics was by my colleague, Ethan Mollick (wait, that's me!).

In our first paper, we had 758 management consultants do a series of consulting tasks including writing and solving consulting problems. We found a 12.2% to 25.7% increase in performance of those using ChatGPT, depending on task. We also found an equalizing impact of AI. Those in the bottom quartile of performers on a pre-study test of common consulting tasks improved more, as did those who did worse on the tasks in general.

We found that good prompting (using techniques like role prompting, engaging in dialogue) mattered in generating high quality results. In a follow-up, we had consultants engage in a longer project (about 3 hours) and found that the team with AI produced better work.

Other researchers have found similar or greater results, but with larger performance improvements. Noy & Zhang asked professional and managerial workers to complete realistic tasks, like writing a pitch to senior managers about an innovative use of AI in a company and had them compared to non-AI users. They found a 40% increase in worker output, measured as time per task, across a broad of professionals doing realistic writing tasks. They also found that AI was more helpful to lower-skilled workers, and that experience with AI mattered for getting the most out of it.

Intel compared teams using and not using GPT-4 in a variety of typical-for-Intel tasks, including drafting marketing personals and creating digital patent drawings. They found the GPT-4 team completed tasks 43% faster and were rated as having higher-quality output. Note that they paid a lot of attention to teaching people to use GPT-4 in their study, creating a custom handbook and offering teaching sessions.

A big study by Stanford & MIT looked at 1000 customer service agents and had them take writing tasks with and without Claude (one of the top LLMs). The AI increased productivity by 35%, with the largest improvements for agents with lower writing ability. They also tracked work over 6 weeks, and found that productivity improved over time, indicating longer-term benefits.