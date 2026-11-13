# Can We Trust a Passing Agent?

Auditing and Repairing Coding-Agent Evaluation Through a Gemma 4 Case Study

TEBench can omit a required test when its annotation and declaration share a source line. The omission affects reference extraction and test selection. This repository contains a repair that reads compiled test annotations within a fixed method scope and checks that every required invocation completes.

The main experiment covers two source-exposed tasks, Jsoup and Commons Codec, with seven equivalent source layouts each. All transformed test classfiles match their original layout within the same candidate role. Researchers authored the incorrect candidate fixtures.

| Selector | Complete task-layouts | Nonempty authored-candidate passes | Empty selections |
|---|---|---|---|
| Released filter | 2/14 | 2/14 | 10/14 |
| Same-line patch | 5/14 | 1/14 | 8/14 |
| Compiled inventory | 14/14 | 0/14 | 0/14 |

The repaired selector accepts all 14 developer-control layouts and rejects all 14 incorrect-candidate layouts. The 14 layouts are dependent perturbations of two tasks. The execution contract marks missing or incomplete invocations as INCOMPLETE.

## Files

| File | Purpose |
|---|---|
| `EVALUATOR_LAYOUT_REPLAY_KIT_v1.zip` | Main selector repair, source fixtures, native evidence, listener, count contract and dependency manifest |
| `GEMMA_PAIRED_REPAIR_REPLAY_KIT_v2.zip` | Secondary Gemma E4B pilot, saved responses, native grades, provenance and coverage diagnostic |
| `reviewer.ipynb` | Recorded evidence replay, source identities and native reproduction instructions |
| `SHA256SUMS` | SHA256 digests for the files in this release |
| `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.txt` | License and source attribution |
| `CITATION.cff` | Citation metadata for this resource |
| `COMPATIBILITY.json` | Fresh CPU checks of the upstream-fetch packaging change |

The main selector ZIP is unchanged. Secondary kit v2 removes the copied TEBench predicate and fetches the checksum-identical function during setup. Its recorded evidence, model responses and native results are byte-identical to v1. Updated manifests identify the new packaging. The public notebook preserves the recorded outputs from Kaggle version 6. Section 1b replaces its embedded upstream functions with checksum-verified downloads. The submitted Kaggle artifacts remain unchanged. Its default cells check saved evidence. Section 1b downloads checksum-pinned upstream functions on first use and caches them locally. Run with internet access initially, or run `python3.12 fetch_tebench.py` from the notebook working directory first. Later cached replay works offline. Fresh native execution uses the commands below.

## Reproduce the main repair

Use Linux amd64, Python 3.12 and a Java 17 JDK. The recorded workers used Python 3.12.15 and Debian OpenJDK 17.0.20.1, with one CPU and one GiB RAM. Setup downloads hash-pinned public dependencies. Native reproduction needs no model, GPU, cloud account, credentials or private research packet.

### 1. Check and extract the release

Download the repository files or clone this repository. From its root, check the release digests and extract the main kit into a new directory.

```bash
sha256sum -c SHA256SUMS
unzip EVALUATOR_LAYOUT_REPLAY_KIT_v1.zip -d evaluator_replay
cd evaluator_replay
sha256sum -c SHA256SUMS
```

On macOS, `shasum -a 256 -c SHA256SUMS` checks file digests. Run the native experiment in Linux.

### 2. Set the toolchain and run both cases

The JDK path below is the recorded Debian path. Change it if your Java 17 JDK is installed elsewhere. Use fresh output directories.

```bash
python3.12 --version
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
"$JAVA_HOME/bin/java" -version
"$JAVA_HOME/bin/javac" -version
python3.12 fetch_dependencies.py
python3.12 run_study.py --case jsoup --java-home "$JAVA_HOME" --dependencies dependencies --output results-jsoup
python3.12 run_study.py --case codec --java-home "$JAVA_HOME" --dependencies dependencies --output results-codec
```

### 3. Read the reports

```bash
python3.12 -m json.tool results-jsoup/REPORT.json
python3.12 -m json.tool results-codec/REPORT.json
```

Each case should record 42 native executions. Both reports should have `completed`, `all_variants_qualified` and `all_complete_controls_match` set to true, with no reported errors. Compare the combined selector counts with the table above. Read the per-variant native records when any field differs. A zero driver exit alone is insufficient.

For Figure 1, inspect the original-layout authored Jsoup candidate. The released selector starts one passing test and receives contract INCOMPLETE. The compiled inventory starts two tests, including one assertion failure, and receives contract FAIL. Both observations belong to the 84-execution study.

Compiler versions can change artifact hashes. Exact cross-run bytecode comparisons require the recorded JDK. Within each run, every admitted transformed classfile map must match its original role.

The upstream-fetch change passed a fresh Azure CPU check of all seven notebook code cells, cached offline replay, the full secondary evidence archive and the documented native Jsoup recipe. The native statuses, feedback and fault qualification matched the saved initial observations. `COMPATIBILITY.json` records the checked archive hash and the final packaging difference.

## Secondary Gemma evidence

The notebook separately regrades four saved Gemma 4 31B identification predictions on the affected Jsoup task and four predictions on an unaffected control. The fixed affected predictions change from F1 zero to one under a layout intervention that preserves the compiled program.

The E4B kit contains five source-exposed method units from four historical commits, with two seeds per unit. Its planned grader-feedback contrast never activates. Agent-learning effects remain unmeasured. Missing responses, admission failures and compilation failures are retained.

The coverage example is post-hoc and limited to one changed production class. The saved Gemma test and developer reference have equal probe coverage but different historical-fault outcomes. The Figure 5 calculation reconstructs depicted method sets without the original agent patches. Neither analysis establishes a leaderboard ranking change.

For the secondary native commands, extract the E4B kit and follow its `README.txt`, or Section 7 of the notebook. The plan is at `kit/PLAN.json` after extraction. Saved model outputs must remain unchanged. New inference would be a new experiment.

## Scope

The repair covers annotation classification within a declared method inventory and fixed invocation counts. Complete repository-level diff extraction and dynamic-provider counts require further validation. Population defect rates, general coding improvement, post-training and swarm efficiency remain unmeasured.

Earlier full Maven and Codec worker recipes require retained private input packets. Their saved-record projections are included in the notebook. The public native selector study above is a separate experiment on the same affected tasks and has no private input dependency.

## Sources and license

[Paper and project files on Kaggle](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/writeups/when-a-coding-agent-evaluator-misses-the-test)

[Reviewer notebook on Kaggle](https://www.kaggle.com/code/dnicholson/gemma-4-evaluator-audit-reviewer-replay)

[TEBench paper](https://arxiv.org/abs/2605.06125) and [inspected source revision](https://github.com/iSEngLab/TEBench/tree/5f607183bd9f29b6c740eae76b0489dd0c7556d5)

Original toolkit code and documentation are provided under Apache License 2.0. TEBench source is excluded from this distribution. Setup fetches the exact upstream functions directly from revision `5f607183bd9f29b6c740eae76b0489dd0c7556d5` and verifies file and function SHA256 hashes. No upstream software license was identified at that revision. Fetched TEBench code remains subject to its upstream terms. Upstream source retains its own licenses and notices, including MIT, Apache 2.0 and LGPL 2.1 or later. See `THIRD_PARTY_NOTICES.txt` and the files inside each kit. Model weights and dependency JARs are not included.
