# Prompt Engineering Is Dead. Long Live Prompt Engineering.

Source: [One Useful Thing Newsletter](https://www.oneusefulthing.org/p/prompt-engineering-is-dead-long-live)
Date: February 13, 2024
Tags: AI, prompting, LLMs, prompt engineering

Prompt engineering, as we know it, is dead, but a new, more interesting version has emerged. Let me explain.

You can divide the original concept of prompt engineering into two distinct approaches. The first is a formal search for specialized prompts that achieve a specific result from a particular AI system. In this approach, prompt engineering consists of a series of tricks and specialized methodologies that can unlock capabilities of language models: chain-of-thought prompting to help AIs reason through a problem, instruction prompting to get them to follow a desired course of action, or system prompts that change the operating parameters of the AI. There have been thousands of papers on these various techniques, and entire companies have been built around finding and leveraging the right prompts. But these techniques are now mostly unnecessary.

The power of prompt engineering is no longer in finding secret, clever instructions that get models to behave differently, but in understanding how this technology works and how to use it. It used to be that prompt engineering was about getting the AI to do things it couldn't normally accomplish; now prompt engineering is about helping AIs do what they can do, and helping humans use these AIs. This version of prompt engineering revolves around two main aspects:

## The Role-Based Prompt

The prompt engineering of today works by giving AI a detailed description of the role you want it to fill and how it should behave in that role. As GPT-4, Claude, Anthropic, and other LLMs get more intelligent and general-purpose, prompt engineering is shifting from trying to coax the AI into doing something difficult to having a clear conversation with the AI about what you want from it.

So if I'm working on a report and I want feedback on whether the arguments are compelling, I might try the following prompt:

"I'd like you to review a report, with a background as an experienced executive in finance, looking at my arguments and suggesting improvements in structure, persuasiveness, and evidence. Use bullet points for clarity."

The approach here is not a special trick to "unlock" capabilities in the AI. Instead it's just a clear and specific statement defining what kind of help I need, and the context in which that help will be delivered. I found it works better to define a background and domain of expertise, the tasks you need done, and some additional guidance on how the results should be structured.

## Designing a Custom Agent

The other major path of prompt engineering today involves creating agents that are specifically designed to do a certain task or to have a certain character. The system prompt - the initial instructions given to an AI  before any user interaction - has become a critical tool for this.

A good example of this approach is the creation of custom GPTs in OpenAI's system, or the use of specialized domains that can affect all subsequent interactions. These might include specialized instructions, reference materials, custom code execution, or specific response styles.

This means creating a clear set of instructions and resources that an AI has access to as it tries to respond, rather than trying to figure out clever ways to force it to behave as you want.

## The Death and Rebirth of Prompt Engineering

Specialized prompting techniques haven't disappeared completely. They still exist in academic papers and still sometimes work with newer models, though they're less reliable. The difference is that we increasingly operate directly with AIs, having a conversation about what we need, rather than trying to manipulate them into doing what we want.

The skill of engineering effective prompts hasn't gone away, but it's shifted from knowing special incantations to understanding how to communicate clearly about our needs - defining roles, providing clear instructions, and sometimes creating specialized agents. It's simultaneously less magical and more powerful, focused on augmenting the already-powerful capabilities of modern LLMs rather than forcing them to do something they weren't designed for.

So prompt engineering as we knew it is dead - replaced by a more natural approach to working with AI systems. The tricks still lurk in various specialized applications, but day-to-day work with AI is now about being clear, specific, and conversational.

## How to Write Good Prompts Now

This shift leaves us with a more straightforward approach to effective prompting:

1. **Define the role or expertise you need the AI to embody**
   - Be specific about the domain of knowledge
   - Define the level of expertise required
   - Specify any particular perspective you want it to take

2. **Explain the task clearly**
   - What exactly do you want the AI to do?
   - What format should the response take?
   - What are the success criteria for a good response?

3. **Provide context and constraints**
   - Give relevant background information
   - Specify any particular approaches or methodologies to use or avoid
   - Set boundaries on the scope of the response

4. **Request specific output formats when helpful**
   - Ask for bullet points, tables, or other structured formats when appropriate
   - Specify tone, length, and level of detail

5. **Iterate through conversation**
   - Treat the AI as a collaborative partner
   - Ask follow-up questions to refine responses
   - Request changes to format, tone, or content as needed

This approach is less about finding secret methods to unlock AI capabilities and more about clear communication - exactly the kind of skill that's valuable in human-to-human interactions as well.