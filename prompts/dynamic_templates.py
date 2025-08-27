def build_question_generation_instructions(tech_list, retrieved_context, n=5):
    return {
        "system": "Generate concise, focused technical screening questions tied to the provided technologies and context.",
        "user": {
            "technologies": tech_list,
            "context_snippets": retrieved_context,
            "count": n,
            "difficulty_mix": {"easy":1,"medium":3,"hard":1},
            "format": {
                "type":"json",
                "schema":{
                    "items":[{"topic":"str","question":"str","difficulty":"easy|medium|hard"}]
                }
            }
        }
    }
