# Emergency: Actions minutes or budget exhausted

Symptom: workflows fail or never start in **every** private repo on the account, often with no log
(the job never begins), and scheduled workflows "stop working" at the same time.

## 1. Confirm

```bash
gh run list -R OWNER/REPO --limit 5 --json workflowName,event,conclusion,createdAt
```

Several repos failing from the same hour with no code change point to the quota. The confirmation
is in *Settings → Billing → Usage* (the billing API needs the `user` scope, or org admin).

## 2. Restore what serves users first

List the scheduled workflows of each repo on the account (`gh api repos/OWNER/REPO/actions/workflows`)
and find the ones a product depends on (publishing, notifications, data sync, backups).

1. **Disable the heavy workflow** so it does not eat the new headroom:
   `gh workflow disable <name> -R OWNER/REPO`.
2. **Raise the budget just enough** in *Settings → Billing → Budgets*. This is spending: the owner
   decides, not the agent. Size it from the product workflows' daily usage until the end of the
   billing cycle, and record it wherever the project tracks spending.
3. **Re-run the critical crons by hand** (`gh workflow run <name> -R OWNER/REPO`) and check that they
   finish with `success`.

## 3. Fix the cause

Go back to the flow in `SKILL.md`: diagnosis, rules and test. Re-enable the heavy workflow
(`gh workflow enable`) only once it follows the rules or runs on a self-hosted runner.
