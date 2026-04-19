import gradio as gr
from datetime import datetime
from groq import Groq
import traceback
import json
import os
from dotenv import load_dotenv
from executor import DockerTestExecutor

load_dotenv()

# Initialize Docker Executor
docker_executor = DockerTestExecutor()

api_key_coder = os.getenv('GROQ_API_KEY')
if not api_key_coder:
    raise ValueError("GROQ_API_KEY not found in environment")
  #############
class GroqLLM:
    def __init__(self, api_key, model="llama-3.3-70b-versatile", temperature=0.0):
        self.client = Groq(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def invoke(self, prompt):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"LLM Error: {str(e)}"

llm = GroqLLM(api_key=api_key_coder)
############№
def process_test_with_docker(script_text, testcase_text, language):
    try:
        if not script_text.strip():
            return "⛔ Please paste a test script."
        
        result = docker_executor.execute_test(language, script_text)
        
        if result["success"]:
            return f"""
# ✅ Test PASSED!

## Execution Results:
{result['stdout']}

## Status: **PASSED** - No healing needed!
"""
        
        analysis_prompt = f"""
Test failed in {language} language.

Test Script:
```{language}
{script_text}

Error:
{result['error']}

Output:
{result['stdout']}

Analyze the failure and provide a corrected version of the test script.
Return ONLY valid {language} code that would pass the test.
"""

        healed_code = llm.invoke(analysis_prompt)
        healed_result = docker_executor.execute_test(language, healed_code)

        return f"""

🔧 HealTest AI Report

Original Test Status: ❌ FAILED

Error Details:
{result['error'][:500] if result['error'] else result['stdout'][:500]}

Healing Attempt: 🤖

Healed Code:
{healed_code[:1000]}

Healed Test Status: {'✅ PASSED' if healed_result['success'] else '❌ FAILED'}

Healed Test Output:
{healed_result['stdout'][:500] if healed_result['stdout'] else healed_result['error'][:500]}
"""
    except Exception as e:
        return f"❌ Error: {str(e)}\n\n{traceback.format_exc()}"
      ################



## 🧩 الخلية 4: Synthetic Data Generator

class SyntheticDataGenerator:
    def __init__(self, llm):
        self.llm = llm

    def generate_data(self, schema_description, data_type="json", language="Python", record_count=5):
        prompt = f"""
Generate {record_count} synthetic test records in {data_type.upper()} format.

Schema: {schema_description}
Target Language: {language}

Requirements:
- Generate realistic, diverse data
- Include edge cases
- Format as valid {data_type.upper()}
- Ready to use in {language} tests

Output ONLY the data, no explanations.
"""
        return self.llm.invoke(prompt)

synthetic_generator = SyntheticDataGenerator(llm)
##################
class KnowledgeInput:
    def __init__(self, requirements=None, dom=None, api_spec=None, user_flows=None, source_code=None, recording=None):
        self.requirements = requirements
        self.dom = dom
        self.api_spec = api_spec
        self.user_flows = user_flows
        self.source_code = source_code
        self.recording = recording


class SmartQASystem:
    def __init__(self, llm):
        self.llm = llm

    def run(self, knowledge, language="Python"):
        prompt = f"Generate professional test cases for {language} testing.\n\nAvailable Information:\n"

        if knowledge.requirements:
            prompt += f"\nRequirements:\n{knowledge.requirements}\n"
        if knowledge.dom:
            prompt += f"\nUI/DOM:\n{knowledge.dom}\n"
        if knowledge.api_spec:
            prompt += f"\nAPI Spec:\n{knowledge.api_spec}\n"

        prompt += """
Generate structured test cases with:
- Test Case ID
- Title
- Type
- Priority
- Preconditions
- Test Steps
- Expected Results
"""

        test_cases = self.llm.invoke(prompt)

        summary = f"""
📊 Generation Summary
Language: {language}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Status: ✅ Complete
"""

        return {"test_cases": test_cases, "summary": summary}


smartqa = SmartQASystem(llm)
###############
with gr.Blocks(title="QA Suite with Docker", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🐳 QA Suite")

    with gr.Tab("🔧 HealTest AI"):
        heal_language = gr.Dropdown(["python", "javascript", "java", "csharp"], value="python")
        heal_script = gr.Code(lines=10)
        heal_btn = gr.Button("Run")
        heal_output = gr.Markdown()

        heal_btn.click(
            process_test_with_docker,
            inputs=[heal_script, gr.Textbox(), heal_language],
            outputs=heal_output
        )

    with gr.Tab("🎯 SmartQA"):
        req = gr.Textbox(lines=5)
        btn = gr.Button("Generate")
        out = gr.Markdown()

        def generate(req):
            k = KnowledgeInput(requirements=req)
            r = smartqa.run(k)
            return r["test_cases"]

        btn.click(generate, inputs=req, outputs=out)
      ############
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
