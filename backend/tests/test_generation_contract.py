import json
import unittest
from backend.app.rag.generation.grounding import Draft, GroundingFailure, messages_for, validate_draft


class GenerationContractTests(unittest.TestCase):
    def test_prompt_includes_actual_schema_and_bounded_output_instructions(self):
        system=messages_for('رؤيا',[])[0]['content']
        schema=json.loads(system.split('authoritative for the response structure:\n',1)[1])
        self.assertEqual(schema,Draft.model_json_schema())
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(schema['properties']['claims']['maxItems'],5)
        self.assertIn('at most THREE claims',system)

    def test_excess_claims_report_limit_without_disclosing_content(self):
        claim={'text':'صياغة تجريبية للاختبار','evidence':[{'source_id':'fixture','quote':'اقتباس تجريبي للاختبار'}]}
        with self.assertRaises(GroundingFailure) as result:
            validate_draft(json.dumps({'insufficient':False,'claims':[claim]*6,'differences':[]}),[])
        self.assertEqual(result.exception.fields,[{'field':'claims','type':'too_long'}])
        self.assertNotIn('تجريبية',str(result.exception.fields))

    def test_unknown_field_name_and_raw_values_are_redacted(self):
        with self.assertRaises(GroundingFailure) as result:
            validate_draft(json.dumps({'insufficient':True,'claims':[],'differences':[],
                                      'private-dream-secret':'private-response-secret'}),[])
        self.assertEqual(result.exception.fields,[{'field':'[extra_field]','type':'extra_forbidden'}])
        self.assertNotIn('private',str(result.exception.fields))

    def test_short_quotes_and_missing_fields_are_diagnostic_not_silently_accepted(self):
        with self.assertRaises(GroundingFailure) as result:
            validate_draft(json.dumps({'insufficient':False,'claims':[{'text':'نص للاختبار','evidence':[{'source_id':'fixture','quote':'قصير'}]}]}),[])
        self.assertIn({'field':'claims.0.evidence.0.quote','type':'string_too_short'},result.exception.fields)
        self.assertIn({'field':'differences','type':'missing'},result.exception.fields)
