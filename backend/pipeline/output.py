"""
output helpers
format pipeline results
serialize documents
"""


# ==================== OUTPUT MIXIN ====================

class OutputMixin:

    def _empty_result(self) -> dict:
        # return empty result
        return {
            "snapshot": "",
            "customer": {},
            "corporate_guarantor": {},
            "high_risk_entities": [],
            "confidence_score": 0.0,
            "documents": [],
            "model_id": self.current_model_id,
            "fact_check_score": None,
        }

    def _format_output(
        self,
        documents,
        snapshot: str,
        profile: dict,
        fact_check_score=None,
        fact_check_details=None,
    ):
        # build output payload
        if not isinstance(profile, dict):
            profile = {}

        # read customer block
        customer = profile.get("customer")
        if not isinstance(customer, dict):
            customer = {}

        # read guarantor block
        corporate_guarantor = profile.get("corporate_guarantor")
        if not isinstance(corporate_guarantor, dict):
            corporate_guarantor = {}

        # read high risk list
        high_risk = profile.get("high_risk_entities")
        if not isinstance(high_risk, list):
            high_risk = []

        # compute snapshot length
        snap_text = snapshot or ""
        snap_len = len(snap_text.strip())

        # read customer fields
        cust_rating = (customer.get("rating") or "").strip()
        cust_esg = (customer.get("esg_scorecard") or "").strip()
        cust_dir = (customer.get("new_director") or "").strip()
        cust_date = (customer.get("appointment_date") or "").strip()

        cust_fields = 0
        if cust_rating:
            cust_fields += 1
        if cust_esg:
            cust_fields += 1
        if cust_dir:
            cust_fields += 1
        if cust_date:
            cust_fields += 1

        # read guarantor fields
        guar_rating = (corporate_guarantor.get("rating") or "").strip()
        guar_esg = (corporate_guarantor.get("esg_scorecard") or "").strip()
        guar_dir = (corporate_guarantor.get("new_director") or "").strip()
        guar_date = (corporate_guarantor.get("appointment_date") or "").strip()

        guar_fields = 0
        if guar_rating:
            guar_fields += 1
        if guar_esg:
            guar_fields += 1
        if guar_dir:
            guar_fields += 1
        if guar_date:
            guar_fields += 1

        # read high risk size
        high_risk_count = len(high_risk)

        # set base confidence
        confidence = 0.2

        # apply snapshot weight
        if snap_len >= 400:
            confidence += 0.3
        elif snap_len >= 200:
            confidence += 0.2
        elif snap_len >= 80:
            confidence += 0.1

        # apply customer weight
        if cust_fields >= 1:
            confidence += 0.2
        if cust_fields >= 3:
            confidence += 0.1

        # apply guarantor weight
        if guar_fields >= 1:
            confidence += 0.1

        # apply high risk weight
        if high_risk_count >= 1:
            confidence += 0.2

        # apply fact check weight
        fc_val = None
        if fact_check_score is not None and bool(self.config.CONFIDENCE_USE_FACT_CHECK):
            # clamp fact check score
            fc_val = float(fact_check_score)
            fc_val = max(0.0, min(1.0, fc_val))

            # read multiplier bounds
            min_mult = float(self.config.CONFIDENCE_FACT_CHECK_MIN_MULT)
            max_mult = float(self.config.CONFIDENCE_FACT_CHECK_MAX_MULT)

            # map into multiplier
            mult = float(min_mult + ((max_mult - min_mult) * fc_val))

            # apply multiplier
            confidence = float(confidence * mult)

        # clamp confidence
        confidence = max(0.0, min(0.95, confidence))

        # print stats
        print(f"[PIPELINE] snapshot length: {snap_len}")
        print(
            f"[PIPELINE] profile parts: "
            f"customer_fields={cust_fields}, "
            f"guarantor_fields={guar_fields}, "
            f"high_risk={high_risk_count}"
        )
        if fc_val is not None:
            print(f"[PIPELINE] fact check score: {fc_val:.3f}")
        print(f"[PIPELINE] confidence score: {confidence:.3f}")

        out = {
            "snapshot": snapshot or "",
            "customer": self._convert_floats(customer),
            "corporate_guarantor": self._convert_floats(corporate_guarantor),
            "high_risk_entities": self._convert_floats(high_risk),
            "confidence_score": float(confidence),
            "documents": self._serialize_documents(documents),
            "fact_check_score": fc_val,
        }

        # attach fact check details
        if fact_check_details is not None:
            out["fact_check"] = self._convert_floats(fact_check_details)

        return out

    def _convert_floats(self, data):
        # convert float types
        if isinstance(data, list):
            # convert list items
            return [self._convert_floats(i) for i in data]

        if isinstance(data, dict):
            # convert dict values
            return {k: self._convert_floats(v) for k, v in data.items()}

        if hasattr(data, "item"):
            # convert numpy scalar
            return data.item()

        return data

    def _serialize_documents(self, documents):
        # serialize haystack docs
        serialized = []
        for d in documents:
            # copy meta dict
            meta = dict(d.meta) if d.meta else {}

            # drop internal keys
            for key in self.config.OUTPUT_META_DROP_KEYS:
                meta.pop(key, None)

            # append serialized row
            serialized.append(
                {
                    "content": d.content,
                    "meta": self._convert_floats(meta),
                }
            )
        return serialized

    def _log_timings(self, timings: dict):
        # print timing table
        print("\n[PIPELINE] step timings:")
        keys = [k for k in timings.keys() if k not in ["total_time"]]
        for key in sorted(keys):
            # read timing value
            val = float(timings.get(key, 0.0))
            print(f"  {key}: {val:.3f}s")

        # print total time
        total = timings.get("total_time")
        if total is not None:
            total_val = float(total)
            print("-" * 20 + "\n")
            print(f"  total_time: {total_val:.3f}s\n")