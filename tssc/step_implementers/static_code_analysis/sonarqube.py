"""Step Implementer for the 'static-code-analysis' step for SonarQube.

Reference:  https://docs.sonarqube.org/latest/analysis/analysis-parameters

Step Configuration
------------------

Step configuration key(s) for this step:

| Key               | Required | Default                   | Description
|-------------------|----------|---------------------------|-----------
| `properties`      | True     | ./sonar-project.proerties | Existing properties
|                   |          |                           | file for SonarQube
| `url`             | True     | None                      | SonarQube host url
|                   |          |                           | (sonar.host.url)
| `username`        | False    | None                      | SonarQube username id
|                   |          |                           | (sonar.login)
| `password`        | False    | None                      | SonarQube password

`username` and `password` can be specifed as runtime arguments.

Expected Previous Step Results
------------------------------

Results expected from previous steps:

| Step Name           |  Key       | Description
|---------------------|------------|------------
| `generate-metadata` | `version`  |  SonarQube project version
|                     |            |  (sonar.projectVersion)

Results
-------

Results output by this step:

| Key                              | Description
|----------------------------------|------------
| `result`                         | A dictionary describing the output \
                                     of this step
| `report-artifacts`               | An array of dictionaries describing \
                                     artifacts generated by this step

Elements in `result` dictionary:

| Key          | Description
|--------------|------------
| `success`    | Boolean value describing success/failure of this step
| `message`    | Human readable message describing results of this step

Elements in `report-artifacts` dictionary:

|  Key         | Description
|--------------|------------
| `name`       | Human readable name for report artifact generated by this step
| `path`       | Absolute path (including transport protocol) to the step report artifact


Examples
--------

Example: Step Configuration (minimal)

    static-code-analysis:
    - implementer: SonarQube
      config:
        url: https://sonarqube.yourcompany.com/

Example: Generated Sonar Scanner Call (uses both step configuration and previous results)

    sonar-scanner
        -Dproject.settings=properties
        -Dsonar.host.url=url
        -Dsonar.projectVersion=generate-metadata.version
        -Dsonar.projectKey=application-name.service-name

Example: Existing Sonar Properties File (minimal)

    #----- Default SonarQube server
    # TSSC Config requires the url; this will NOT be used
    #   sonar.host.url=https://sonarqube-sonarqube.apps.tssc.rht-set.com/
    # TSSC will override:
    #   sonar.projectKey
    #   sonar.projectVersion
    #   sonar.working.directory
    # TSSC recommendation:
    #   Set qualitygate wait to true to stop the pipeline
    #   when the threshold of errors is reached.
    #   Regardless, see the SonarQube dashboard for details.
    sonar.qualitygate.wait=true

    # --- optional ---
    # Optional defaults to project key,
    sonar.projectName=TSSC Quarkus Reference App

    # --- optional ---
    # Encoding of the source code. Default is default system encoding
    sonar.sourceEncoding=UTF-8

    # --- java basic properties ---
    sonar.sources=src/main/java/
    sonar.java.libraries=target/*.jar
    sonar.java.binaries=target/classes/org/acme/rest/json
    sonar.java.test.binaries=target/test-classes/org/acme/rest/json

    # --- java reporting properties ---
    #sonar.coverage.jacoco.xmlReportPaths=target/site/jacoco
    #sonar.core.codeCoveragePlugin=jacoco

"""

import os
import sys
import sh
from tssc import StepImplementer
from tssc.step_result import StepResult

DEFAULT_CONFIG = {
    'properties': './sonar-project.properties'
}

AUTHENTICATION_CONFIG = {
    'username': None,
    'password': None
}

REQUIRED_CONFIG_KEYS = [
    'url',
    'application-name',
    'service-name'
]


class SonarQube(StepImplementer):
    """
    StepImplementer for the tag-source step for SonarQube.
    """

    @staticmethod
    def step_implementer_config_defaults():
        """
        Getter for the StepImplementer's configuration defaults.

        Notes
        -----
        These are the lowest precedence configuration values.

        Returns
        -------
        dict
            Default values to use for step configuration values.
        """
        return DEFAULT_CONFIG

    @staticmethod
    def required_runtime_step_config_keys():
        """
        Getter for step configuration keys that are required before running the step.

        See Also
        --------
        _validate_runtime_step_config

        Returns
        -------
        array_list
            Array of configuration keys that are required before running the step.
        """
        return REQUIRED_CONFIG_KEYS

    def _validate_runtime_step_config(self, runtime_step_config):
        """
        Validates the given `runtime_step_config` against the required step configuration keys.

        Parameters
        ----------
        runtime_step_config : dict
            Step configuration to use when the StepImplementer runs the step with all of the
            various static, runtime, defaults, and environment configuration munged together.

        Raises
        ------
        AssertionError
            If the given `runtime_step_config` is not valid with a message as to why.
        """
        super()._validate_runtime_step_config(runtime_step_config)  # pylint: disable=protected-access

        assert (
            all(element in runtime_step_config for element in AUTHENTICATION_CONFIG) or not any(
                element in runtime_step_config for element in AUTHENTICATION_CONFIG) \
            ), 'Either username or password is not set. Neither or both must be set.'

    def _run_step(self):
        """Runs the TSSC step implemented by this StepImplementer.

        Returns
        -------
        StepResult
            Results of running this step.
        """

        step_result = StepResult.from_step_implementer(self)

        # Optional: username and password
        username = ''
        password = ''
        if self.has_config_value(AUTHENTICATION_CONFIG):
            if (self.get_config_value('username')
                    and self.get_config_value('password')):
                username = self.get_config_value('username')
                password = self.get_config_value('password')

        # Required: Get the generate-metadata.version
        version = self.get_result_value(artifact_name='version')
        if version is None:
            step_result.success = False
            step_result.message = 'Severe error: Generate-metadata results is missing a version tag'
            return step_result

        # Required: properties and exists
        properties_file = self.get_config_value('properties')
        if not properties_file or not os.path.exists(properties_file):
            step_result.success = False
            step_result.message = f'Properties file in tssc config not found: {properties_file}'
            return step_result

        try:
            # Hint:  Call sonar-scanner with sh.sonar_scanner
            #    https://amoffat.github.io/sh/sections/faq.html
            working_directory = self.work_dir_path
            if username == '':
                sh.sonar_scanner(  # pylint: disable=no-member
                    '-Dproject.settings=' + self.get_config_value('properties'),
                    '-Dsonar.host.url=' + self.get_config_value('url'),
                    '-Dsonar.projectVersion=' + version,
                    '-Dsonar.projectKey=' + \
                        self.get_config_value('application-name') + \
                        ':' + \
                        self.get_config_value('service-name'),
                    '-Dsonar.working.directory=' + working_directory,
                    _out=sys.stdout,
                    _err=sys.stderr
                )

            else:
                sh.sonar_scanner(  # pylint: disable=no-member
                    '-Dproject.settings=' + self.get_config_value('properties'),
                    '-Dsonar.host.url=' + self.get_config_value('url'),
                    '-Dsonar.projectVersion=' + version,
                    '-Dsonar.projectKey=' + \
                        self.get_config_value('application-name') + \
                        ':' + \
                        self.get_config_value('service-name'),
                    '-Dsonar.login=' + username,
                    '-Dsonar.password=' + password,
                    '-Dsonar.working.directory=' + working_directory,
                    _out=sys.stdout,
                    _err=sys.stderr
                )

        except sh.ErrorReturnCode as error:  # pylint: disable=undefined-variable
            raise RuntimeError('Error invoking sonarscanner: {all}'.format(all=error)) from error

        step_result.add_artifact(
            name = 'sonarqube_result_set',
            value = f'file://{working_directory}/report-task.txt',
            value_type = 'file'
        )
        return step_result
