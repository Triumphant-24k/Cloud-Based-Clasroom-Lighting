from types import SimpleNamespace
import pytest
from backend.config import load_config
from backend.services.cloud import CloudService

CHECK_BUDGET=CloudService.check_credit_budget

@pytest.mark.parametrize('remaining,plan_type,allowed',[(120,'FREE',True),(50,'FREE',True),(40,'FREE',False),(0,'FREE',False),(120,'PAID',False)])
def test_original_budget_excludes_earned_bonus(remaining,plan_type,allowed):
    c,z,m=load_config();service=CloudService(c,m)
    activity={'status':'COMPLETED','reward':{'credit':{'amount':20}}}
    paginator=SimpleNamespace(paginate=lambda:[{'activities':[activity]}])
    calls=[]
    def plan():
        calls.append(True)
        return {'accountPlanType':plan_type,'accountPlanStatus':'ACTIVE','accountPlanRemainingCredits':{'amount':remaining}}
    service._billing=SimpleNamespace(get_account_plan_state=plan,get_paginator=lambda name:paginator)
    if allowed:
        CHECK_BUDGET(service);CHECK_BUDGET(service)
        assert len(calls)==1
    else:
        with pytest.raises(ConnectionError):CHECK_BUDGET(service)


def test_missing_billing_data_fails_closed():
    c,z,m=load_config();service=CloudService(c,m)
    service._billing=SimpleNamespace(get_account_plan_state=lambda:{})
    with pytest.raises(KeyError):CHECK_BUDGET(service)
