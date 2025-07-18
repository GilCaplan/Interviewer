"""
Utility functions for safely executing user code
"""

import os
import tempfile
import subprocess
import time
import signal
import logging

# Setup logging
logger = logging.getLogger(__name__)


def run_python_code(code, test_case, timeout=5):
	"""
    Safely run Python code with a test case

    Args:
        code (str): The Python code to run
        test_case (dict): Dictionary containing test case information
        timeout (int): Maximum execution time in seconds

    Returns:
        dict: Results of the test execution
    """
	result = {
		"passed": False,
		"actual": "",
		"error": None
	}

	try:
		# Create a temporary file with the user's code and test
		with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
			function_name = test_case.get("functionName", "solution")

			# Write the user's code
			f.write(code.encode())

			# Add test runner code
			test_code = f"\n\n# Test runner\nif __name__ == '__main__':\n"
			test_code += f"    try:\n"
			test_code += f"        result = {function_name}({test_case['input']})\n"
			test_code += f"        print(repr(result))\n"
			test_code += f"    except Exception as e:\n"
			test_code += f"        print(f'Error: {{str(e)}}')\n"

			f.write(test_code.encode())
			temp_filename = f.name

		# Run the code in a subprocess with timeout
		try:
			process = subprocess.Popen(
				['python3', temp_filename],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				preexec_fn=os.setsid
			)

			# Wait for the process to complete with timeout
			try:
				stdout, stderr = process.communicate(timeout=timeout)

				# Get the result
				if process.returncode == 0:
					actual_output = stdout.decode().strip()
					if actual_output.startswith("Error:"):
						result["actual"] = actual_output
					else:
						result["actual"] = actual_output

						# Compare with expected output (with flexible comparison)
						expected = test_case["expectedOutput"].strip()
						# Try to normalize both outputs for comparison
						try:
							# For boolean values
							if expected.lower() in ["true", "false"]:
								expected_eval = expected.lower() == "true"
								actual_eval = eval(actual_output)
								result["passed"] = expected_eval == actual_eval
							# For other values
							else:
								expected_eval = eval(expected)
								actual_eval = eval(actual_output)
								result["passed"] = expected_eval == actual_eval
						except:
							# Fall back to string comparison
							result["passed"] = expected == actual_output
				else:
					result["actual"] = f"Error: {stderr.decode()}"
			except subprocess.TimeoutExpired:
				# Kill the process if it times out
				os.killpg(os.getpgid(process.pid), signal.SIGTERM)
				result["actual"] = f"Error: Execution timed out after {timeout} seconds"
				result["error"] = "timeout"

		except Exception as e:
			logger.error(f"Error running subprocess: {str(e)}")
			result["actual"] = f"Error: Failed to execute code - {str(e)}"
			result["error"] = "execution"

		# Clean up temp file
		try:
			os.unlink(temp_filename)
		except:
			pass

	except Exception as e:
		logger.error(f"Error in run_python_code: {str(e)}")
		result["actual"] = f"Error: {str(e)}"
		result["error"] = "system"

	return result


def safe_execute_code(code, test_cases, language="python"):
	"""
    Execute code safely with multiple test cases

    Args:
        code (str): User code to execute
        test_cases (list): List of test case dictionaries
        language (str): Programming language (only python supported for now)

    Returns:
        tuple: (list of test results, bool indicating if all tests passed)
    """
	results = []

	if language != "python":
		# Only Python supported for now
		for idx, test_case in enumerate(test_cases):
			results.append({
				"id": idx,
				"name": f"Test Case {idx + 1}",
				"input": test_case.get("input", ""),
				"expected": test_case.get("expectedOutput", ""),
				"actual": "Error: Language not supported yet",
				"passed": False
			})
		return results, False

	for idx, test_case in enumerate(test_cases):
		test_result = {
			"id": idx,
			"name": f"Test Case {idx + 1}",
			"input": test_case.get("input", ""),
			"expected": test_case.get("expectedOutput", "")
		}

		# Run the test
		execution_result = run_python_code(code, test_case)

		# Update the test result
		test_result["actual"] = execution_result["actual"]
		test_result["passed"] = execution_result["passed"]

		results.append(test_result)

	# Check if all tests passed
	all_passed = all(result["passed"] for result in results)

	return results, all_passed