import healthchain as hc
import logging

from healthchain.models.data.ccddata import CcdData
from healthchain.models.data.concept import (
    AllergyConcept,
    Concept,
    MedicationConcept,
    ProblemConcept,
    Quantity,
)
from healthchain.use_cases import ClinicalDecisionSupport
from healthchain.data_generators import CdsDataGenerator
from healthchain.models import Card, CdsFhirData, CDSRequest

from healthchain.use_cases.clindoc import ClinicalDocumentation
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from typing import List
from dotenv import load_dotenv

load_dotenv()


log = logging.getLogger("healthchain")
log.setLevel(logging.DEBUG)


@hc.sandbox
class MyCoolSandbox(ClinicalDecisionSupport):
    def __init__(self, testing=True):
        self.testing = testing
        self.chain = self._init_llm_chain()
        self.data_generator = CdsDataGenerator()

    def _init_llm_chain(self):
        prompt = PromptTemplate.from_template(
            "Extract conditions from the FHIR resource below and summarize in one sentence using simple language \n'''{text}'''"
        )
        model = ChatOpenAI(model="gpt-4o")
        parser = StrOutputParser()

        chain = prompt | model | parser
        return chain

    @hc.ehr(workflow="patient-view")
    def load_data_in_client(self) -> CdsFhirData:
        data = self.data_generator.generate()
        return data

    @hc.api
    def my_service(self, request: CDSRequest) -> List[Card]:
        if self.testing:
            result = "test"
        else:
            result = self.chain.invoke(str(request.prefetch))

        return Card(
            summary="Patient summary",
            indicator="info",
            source={"label": "openai"},
            detail=result,
        )


@hc.sandbox
class NotereaderSandbox(ClinicalDocumentation):
    def __init__(self):
        self.overwrite = True

    @hc.ehr(workflow="sign-note-inpatient")
    def load_data_in_client(self) -> CcdData:
        # data = self.data_generator.generate()
        # return data

        with open("./resources/uclh_cda.xml", "r") as file:
            xml_string = file.read()

        return CcdData(cda_xml=xml_string)

    @hc.api
    def my_service(self, ccd_data: CcdData) -> CcdData:
        print(ccd_data.problems)
        print(ccd_data.medications)
        print(ccd_data.allergies)

        new_problem = ProblemConcept(
            code="38341003",
            code_system="2.16.840.1.113883.6.96",
            code_system_name="SNOMED CT",
            display_name="Hypertension",
        )
        new_other_problem = ProblemConcept(
            code="12341",
            code_system="2.16.840.1.113883.6.96",
            code_system_name="SNOMED CT",
            display_name="Diabetes",
        )
        new_allergy = AllergyConcept(
            code="70618",
            code_system="2.16.840.1.113883.6.96",
            code_system_name="SNOMED CT",
            display_name="Allergy to peanuts",
        )
        another_allergy = AllergyConcept(
            code="12344",
            code_system="2.16.840.1.113883.6.96",
            code_system_name="SNOMED CT",
            display_name="CATS",
        )
        new_medication = MedicationConcept(
            code="197361",
            code_system="2.16.840.1.113883.6.88",
            code_system_name="RxNorm",
            display_name="Lisinopril 10 MG Oral Tablet",
            dosage=Quantity(value=10, unit="mg"),
            route=Concept(
                code="26643006",
                code_system="2.16.840.1.113883.6.96",
                code_system_name="SNOMED CT",
                display_name="Oral",
            ),
        )
        ccd_data.problems = [new_problem, new_other_problem]
        ccd_data.allergies = [new_allergy, another_allergy]
        ccd_data.medications = [new_medication]

        print(ccd_data.note)

        return ccd_data


if __name__ == "__main__":
    # cds = MyCoolSandbox()
    # cds.start_sandbox()

    cds = NotereaderSandbox()
    cds.start_sandbox()
