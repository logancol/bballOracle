# NBA Oracle

Natural language querying web tool for basketball enthusiasts to derive exploratory insights from NBA play-by-play data.

## What does it do?

At the moment, NBAOracle exposes one endpoint (outside of user auth) that allows a client to ask NBA statistical questions that can be answered through some transformation of NBA play-by-play data. It relies on OpenAI's GPT 5.2 to generate efficient SQL queries from natural language user questions, validates and runs these queries against a PostgreSQL database, then provides an interpretted result. This project is still in its relatively early stages and, due to the fallible nature of LLMs, it will be liable to make mistakes for the forseeable future. That being said, the goal is for NBAOracle to be another tool in the belt of statistically-inclined sports enthusiasts to perform exploratory analysis and derive neat insights.

## Example Usage

## Current Limitations
