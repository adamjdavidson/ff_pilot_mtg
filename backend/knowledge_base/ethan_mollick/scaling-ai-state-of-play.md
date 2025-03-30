# Scaling: The State of Play in AI

Source: [One Useful Thing Newsletter](https://www.oneusefulthing.org/p/scaling-the-state-of-play-in-ai)
Date: September 16, 2024
Tags: AI, scaling, LLM, frontier models, GPT, Claude, Gemini, reasoning

I wanted to talk about what is happening with Large Language Models (LLMs) at the frontier, because there has been a lot of news that matters lately, especially for people trying to use AI for work or school. I've now spent quite a bit of time with all of the latest models, and I think I can map out the state of the art a bit, as well as what comes next. For those who want something a little more accessible, I also made a short explainer video (3 min) about the latest model releases and how to think about all of it, which you can find on Twitter/X or LinkedIn. But here, I want to go into more detail.

## The scaling laws: it's like Moore's Law for AI

I first started thinking about scaling laws for LLMs in this newsletter a while ago. The idea is simple: if you make an LLM larger (more parameters), train it on more data (more tokens), and use more computation (more FLOPs, which are basically operations), then the model gets better. Newer research suggests that some of these trends are exponential. Larger models are better models. The relationship looks something like this: for every additional 10x increase in computation, fundamental model performance increases by around 0.1 points. That is a small number, but it means capabilities go up quickly, since the scale of calculation is now massive.

And we've seen this happen. The progress in models over the last decade has been dramatic, leading inevitably to today. We're probably getting to the edge of current scaling laws, but the fact that this has worked well so far means we can reliably say we will see progress.

Scaling comes with an enormous cost. I think it makes sense to talk about model generations, defined by the general cost of the most impressive models. There is a lot of silliness in the terminology here, but I wanted to suggest a useful way of thinking about model generations that isn't tied to "A.I doom," but instead is tied to cost to train.

- **Gen1 models** (2022): These are models like ChatGPT-3.5, the first generation of LLMs that were trained for around $10M. They are impressive, and still quite useful. At the time they were unprecedented in their capabilities, though now we see them as limited.

- **Gen2 models** (2023-2024): These are models like GPT-4, and later Claude 3 Opus, and eventually Gemini Pro & Ultra. They cost around $100M. They represent a massive step up in capability, and we are in this generation right now.

- **Gen3 models** (2025-2026?): These models cost around $1B. DeepMind's Gemini Ultra was reported to cost around this amount to train. Next generation models, like GPT-5 and Claude 4, are likely to be in this category. They should be much more capable. We will see multiple examples of these soon.

- **Gen4 models** (2026-?) are models like the ones described in the recent Epoch paper on "Big Models," and would cost $10B+. This feels a ways off for practical and cost reasons, but not science fiction.

Right now in 2024, we are deep into Gen2 models, with Gen3 models on their way - multiple $1B models will be coming out this year or next, including GPT-5 and Claude 4 (though I am speculating on what these unreleased models will be). But even within Gen2, there are very big differences in capabilities. Though all Gen2 models are useful, there are a clear set of frontier models that are more capable.

## Frontier Gen2 models

The best Gen2 models are significantly more capable than other Gen2 models. For context, looking at the HELM benchmark (which offers a reliable way to measure quality across a variety of tasks), you can see that Claude 3.5 Sonnet's performance is dramatically better (71.1%) compared to Llama 70B (58.5%), despite being in the same Gen2 category. 

As of September 2024 (keeping in mind this changes frequently), the top Gen2 models are:

- **GPT-4o** (and the similar GPT-4o mini, which is cheaper)
- **Claude 3.5 Sonnet**
- **Gemini 1.5 Pro**
- **Grok 2**
- **Llama 3.1 405B**

Of this group, the three leading models - GPT-4o, Claude 3.5 Sonnet, and Gemini 1.5 Pro - are close to each other in performance, with slight differences depending on the task. GPT-4o is somewhat better at general knowledge (especially programming), Claude Sonnet 3.5 appears better at longer texts, and Gemini 1.5 Pro is catching up quickly and is very strong at math and coding. There are minor differences across use cases, and personal preference will often determine which model feels better for you.

There's some exciting recent work where researchers essentially grade LLMs on how well they can grade exams. I liked the idea, so I used that approach to make a similar but simpler "professors ranking LLMs" dataset of my own. Claude 3.5 Sonnet earns an A-, GPT-4o an A-, Gemini 1.5 Pro a B+, Llama 3.1 a C+, and Mistral Medium a C. 

## The next frontier: models that "think"

There's another area of scaling that I think is particularly exciting - a new approach where models perform multiple internal reasoning steps before generating their final output. This is conceptually similar to multiple "thinking steps" within the model before it produces an answer.

At its core, this involves the model performing multiple internal reasoning attempts, then analyzing and integrating those attempts to reach a more refined conclusion. This is different from just using more parameters or training data - it's about how the model processes information once it's already built.

This approach has been shown to deliver impressive results. For example, the Claude 3.5 Sonnet model employs this technique, with each "unit of thinking" taking about 1-2 seconds. This process significantly improves accuracy on complex tasks.

What's particularly exciting is that this approach appears to scale similarly to traditional methods - more thinking steps lead to better results - but potentially with better economics since it uses existing models more effectively rather than requiring entirely new, larger ones.

## The future

So where are we going? Moore's Law was one of the most important technological rules in history, predicting the doubling of transistors on integrated circuits approximately every two years. The law is now effectively over, as we've reached physical limits to the size of transistors. Similarly, scaling laws for AI might eventually hit limits, but we're not there yet.

For the foreseeable future, we're likely to see advances in AI capabilities through:

1. Continued scaling of model size, training data, and computation
2. Enhanced "thinking" processes within existing models
3. Better integration of these models into our workflows and tools

In the immediate term, we're seeing fierce competition among the frontier Gen2 models, with all of them steadily improving and finding their specific niches. Looking slightly further ahead, we're moving toward Gen3 models in the $1B range, which should represent another significant step up in capabilities.

While the perfect general purpose AI assistant doesn't exist yet, the current frontier models are already incredibly useful. The best approach is to experiment with different models for different tasks, as each has its own strengths. The next few years will likely bring dramatically improved AI through both traditional scaling and enhanced reasoning approaches.