# system imports
import os
import time
import logging
from pathlib import Path

# third party imports
import openai
import tiktoken

METHODS_PER_BATCH = 4
FILE_PREFIX = ''
print_prompt = False
print_response = True


SYSTEM_PROMPT = f"You are a Expert Software Engineer with experience in Java language."
GUIDELINES_o = """
Sufficient mocking to be provided for all the Objects used in the class.
Use the correct constructors of the source class.
provide the correct parameters to the constructors and the methods.
Each Java class in the source code should have a corresponding unit test class, adhering to a one-to-one mapping principle.
The naming convention for generated unit test classes should align with the naming conventions of the source code, maintaining consistency and clarity.
The generated test code should be compiled and executed using the same version of the source code, ensuring compatibility and accurate test results.
When instantiating objects for testing purposes, preference should be given to using the default constructor, unless specific object initialization requirements necessitate otherwise.
Write unit tests for Java 8 using the JUnit 4 framework to validate the functionality, edge cases, and possible exceptions of the methods provided. 
Ensure that test cases cover typical use cases, boundary conditions, and invalid input scenarios.
"""

GUIDELINES = """
Validates the input parameters.
Returns a result when the inputs are valid.
Throws an exception if the inputs are invalid.
Create separate test case for each invalid input.

Performs some interaction with a repository or external dependency, which should be mocked.
Create unit tests to cover the following scenarios using Mockito for mocking the repository or dependencies:

Test with valid inputs (normal case).
Test with invalid input parameters (input out of valid range or null values).
Test with boundary input values (e.g., minimum and maximum valid values).
Test with unexpected or extreme input values (e.g., empty string, large numbers, negative values).
Test with null or missing dependencies when applicable (e.g., repository returns null or no value).
Verify that the method interacts correctly with the mocked dependencies (e.g., checking if a method is called on the repository).
The service class depends on one or more external dependencies (like a repository, external API, etc.), which should be mocked using Mockito.

Ensure the following in the test cases:

Use Mockito to mock external dependencies (like repositories or services).
Handle the cases where the service method throws exceptions due to invalid inputs.
Use assertions to verify the method’s behavior.
Include test methods for boundary conditions, invalid inputs, and valid inputs.
Check that the service class interacts correctly with the mocked dependencies (e.g., verifying method calls on the mock).
Please provide the complete JUnit 4 unit test code using Mockito, ensuring it covers all scenarios mentioned above.
"""

USER_PROMPT = """
You are tasked with writing unit tests, Please provide the unit tests for "{METHODS}" methods only. Do not leave any test cases out or ask me to add any.
Add the suffix={FILE_SUFFIX} to the test class name. For example if class name is classA and suffix = _post_ then test class name should be classA_post_test.
follow the below mentioned points while generating the unit tests.
{GUIDELINES}
Here is the Java code:
"""

REVIEW_PROMPT = """
You are provided with the LLM generated unit test cases for Java language. Please review the test cases based on the following points.
{GUIDELINES}
Check if all the inputs validation is done.
If all test cases are not present, then add additional test cases in the response.
Here is the Java code followed by Java unit test code:
"""
EXTRACT_METHODS_NAME_PROMPT = """Your task is to find all the methods present in the provided Java file.In your response just include the method name without any signature.
For example
1. `method1`
2. `method2`
Here is the Java code:
"""

llm_config = {
    'endpoint':{
        'api_type':"azure",
        'api_base':"https://aiforce-openai.openai.azure.com/",
        'api_version':"2023-03-15-preview",
        'api_key':"5a60e1c154fa4563b37ca14a4a6c5a0f",
        'deployment_name': 'gpt-4o',
    },
    'model_params':{
        'temperature':0.7,
        'max_tokens':4096,
        'top_p':0.95,
        'frequency_penalty':0,
        'presence_penalty':0
    }
}

# creater logger with file handler
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def debug( msg):
    logger.info( msg)
    print( msg)

class llm_client():
        
    def __init__(self, llm_config):
        openai.api_type = llm_config['endpoint']['api_type']
        openai.api_base = llm_config['endpoint']['api_base']
        openai.api_version = llm_config['endpoint']['api_version']
        openai.api_key = llm_config['endpoint']['api_key']
        self.deployment_name = llm_config['endpoint']['deployment_name']
        self.model_params = llm_config['model_params']

    def run(self, prompt):
        message_text = [{"role" : "system", "content" : SYSTEM_PROMPT}, {"role" : "user", "content" : prompt}]
        response = openai.ChatCompletion.create(
                                engine=self.deployment_name, 
                                messages = message_text,
                                temperature = self.model_params['temperature'],
                                max_tokens=self.model_params['max_tokens'],
                                top_p=self.model_params['top_p'],
                                frequency_penalty=self.model_params['frequency_penalty'],
                                presence_penalty=self.model_params['presence_penalty'],
                                stop=None)
        return response.choices[0]["message"]["content"]

def get_files(path, suffix=['.java']):#read the content form .java files and appending it into the input_files
    text = ""
    path = Path( path)
    input_files = []
    files = [x for x in path.rglob('*') if x.suffix in suffix]
    for file in files:
        content = {}
        with open( file, 'r') as f:
            content[file.stem] = f.read()
        input_files.append( content)
    return input_files

def extract_code( response):#extracted the code form the response generated by llm
    code = ""
    prefix_text = "```java"
    suffix_text = "```"
    start_index = response.find(prefix_text)
    if start_index >= 0:
        response = response[ start_index + len(prefix_text): ]
        end_index = response.find(suffix_text)
        if end_index > 0:
            response = response[:end_index]
        code = response.strip().rstrip()
    return code    
            

class Count_Tokens():
    
    def __init__(self, model_name='gpt-4o'):
        self.encoding = tiktoken.encoding_for_model(model_name)
        self.tokens = 0
    
    def count(self, text='', print_msg = ''):
        self.tokens = 0
        if self.encoding and text:
            try:
                self.tokens = len(self.encoding.encode(text))
            except:
                self.tokens = 0
        if print_msg:
            if self.tokens:
                debug(f"{print_msg}: {self.tokens} tokens")
            elif not self.encoding:
                debug(f"{print_msg}: Encoder is not provided")
            elif not text:
                debug(f"{print_msg}: No data available for encoding")
            else:
                debug(f"{print_msg}: {self.tokens} tokens")
        return self.tokens

    def get(self):
        return self.tokens

def run_usecase(usecase_name, form_data, exec_id, job_name, model_name, *args, **kwargs):
#def run_usecase(usecase_name='Sql_SummariZation', form_data='', exec_id='', job_name='SSZ_20241104125432_ut', model_name='opt', *args, **kwargs):

    
    input_dirpath = "C:/Users/ajay.kumarmeena/OneDrive - HCL TECHNOLOGIES LIMITED/Desktop/Test Case Generation/Scripts"
    output_dirpath = "C:/Users/ajay.kumarmeena/OneDrive - HCL TECHNOLOGIES LIMITED/Desktop/new_tests"

    # input_dirpath = os.path.join("assets", "UploadedData", usecase_name, job_name)
    # output_dirpath = os.path.join("assets", "Result", usecase_name, job_name)
    os.makedirs(output_dirpath, exist_ok=True) # ensure output dir is created
    log_file = ((Path(output_dirpath).parent/'logs')/job_name)/"log.txt"
    log_file.parent.mkdir( parents=True, exist_ok=True)
    logger.addHandler(logging.FileHandler(log_file))
    debug(f"Input dir: {input_dirpath}")
    debug(f"Output dir: {output_dirpath}")
    run_time = time.time()

    input_files = get_files( input_dirpath)
    num_of_files = len( input_files)

    for i in range(num_of_files):
        c=str(i)
        if not input_files:
            raise ValueError("No input files found")
        if c == 1:
            print("Currently working with single file only")
        for k,v in input_files[i].items():
            input_filename = k
            code_text = v
            
        prompt_tokens = 0
        total_tokens = 0
        token_counter = Count_Tokens('gpt-4o')
        debug(f"{input_filename=}")
        client = llm_client(llm_config)
        code_prompt = EXTRACT_METHODS_NAME_PROMPT + code_text
        prompt_tokens += token_counter.count( code_prompt)
        response = client.run( code_prompt)
        total_tokens += token_counter.count( response)
        response = response.split('\n')

        methods = []
        # extract methods name
        for x in response:
            if '`' in x:
                st = x.find('`')
                if st > 0:
                    end = x.rfind('`')
                    if end > 0:
                        methods.append(x[st+1:end])
        debug(f"All {methods=}")
        merged_response = ''
        batches = int(( len(methods) + (METHODS_PER_BATCH - 1)) / METHODS_PER_BATCH)
        for i in range( batches):
            prompt_name = "Unit_test"
            prompt_name = f"{prompt_name}_{i+1}"
            start_index = i * METHODS_PER_BATCH
            end_index = min(start_index + METHODS_PER_BATCH, len(methods))
            method_names = ','.join( methods[start_index:end_index])
            debug(f"{method_names=}")
            code_prompt = USER_PROMPT.format(GUIDELINES=GUIDELINES, METHODS=method_names,FILE_SUFFIX=f"_{i+1}_") + code_text
            prompt_tokens += token_counter.count( code_prompt)
            response = client.run( code_prompt)
            total_tokens += token_counter.count( response)
            response = response.replace('\\n','\n')
            generated_code = extract_code( response)
            file_name = f"{input_filename}_{i+1}_Test.java"
            merged_response += f"\n\n{file_name}\n{generated_code}\n"
            file_name = f"{output_dirpath}/{file_name}"
            debug(f"{file_name=}")
            with open(file_name, 'w') as f:
                f.write( generated_code)


            code_prompt = REVIEW_PROMPT.format(GUIDELINES=GUIDELINES)+ f"```java\n {code_text}\n```\n```unit test code\n{response}\n```"
            with open(f"{output_dirpath}/prompt.txt", 'w') as f:
                f.write( code_prompt)
            prompt_tokens += token_counter.count( code_prompt)
            response = client.run( code_prompt)
            total_tokens += token_counter.count( response)
            response = response.replace('\\n','\n')
            generated_code = extract_code( response)
            file_name = f"{input_filename}_{i+1}_review_Test.java"
            merged_response += f"\n\n{file_name}\n{generated_code}\n"
            file_name = f"{output_dirpath}/{file_name}"
            debug(f"{file_name=}")
            with open(file_name, 'w') as f:
                f.write( generated_code)

        ####[System defined] Append the result received from LLM call
        #append_execution_result(f"Unit Test Generation - {input_filename}", f"Unit Test Generated for {input_filename}", merged_response)

        ####[System defined]. save_execution_summary has to be called at end of execution
        '''save_execution_summary(
            job_name = job_name,
            model_name = model_name,
            prompt_tokens = prompt_tokens,
            total_tokens = total_tokens,
            numof_files = 1,

        )'''

    return {"status": "success", "msg": "Success"}
run_usecase("your_usecase_name", {}, "", "your_job_name", "gpt-4o")