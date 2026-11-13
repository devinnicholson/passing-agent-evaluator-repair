Compiled test inventory and execution-contract study

This research kit contains two source-exposed historical test-evolution cases,
seven source layouts, and three selection strategies. Both incorrect candidates
are authored fixtures. They are not saved real agent predictions. Repetitions,
layouts and candidate roles do not add independent repository tasks.

Requirements

Use Linux amd64, Python 3.12, a Java 17 JDK, one CPU and at least one GiB RAM.
The qualified Azure runs use Debian OpenJDK 17.0.20.1. No model, GPU, Azure SDK,
cloud account, credentials or private input packet is needed by this kit.
The optional download step retrieves pinned public artifacts over HTTPS.

Prepare the public dependencies and pinned original annotation predicate.

  python3 fetch_dependencies.py

Then execute each study in a fresh output path. Set JAVA_HOME to the local JDK.

  python3 run_study.py --case jsoup --java-home "$JAVA_HOME" --dependencies dependencies --output results-jsoup
  python3 run_study.py --case codec --java-home "$JAVA_HOME" --dependencies dependencies --output results-codec

The agent running this research uses Azure CPU for execution, as requested by
the research owner. The kit itself is a portable Linux CPU program.

Methods

PLAN.json fixes the identities and exact invocation counts of two required
Jsoup methods and eight required Commons Codec methods. These finite external
inventories are the declared study scope. This kit does not establish that a
complete repository-level diff extractor finds every required test.

The study compiles production once and each test variant with --release 8 and
-g:none. Debug tables are omitted equally in this new study because some layout
changes add lines. Every admitted layout must produce byte-for-byte identical
test classfile maps to its original layout within the same candidate role.
This qualification does not alter the older paper's debug-preserving controls.
Production and test hashes must remain fixed through each native comparison.

The released strategy invokes the original pinned backward-looking predicate.
The same-line ablation adds only a simple-name check on the declaration line.
The repair reads compiled runtime annotations, including annotations composed
from the supported JUnit markers, and intersects this inventory with the fixed
required identities. It does not infer test status from a source line window.

SuiteProbe.java obtains native invocation identities from JUnit MethodSource
events. execution_contract.py requires exactly the declared number of completed
invocations for each required method. Missing invocations, unknown expected
counts, unexpected methods, container errors, skipped or aborted execution,
and inconsistent native exits produce INCOMPLETE. Fully accounted failures
produce FAIL. PASS requires complete successful execution. Empty selection is
reported separately as EMPTY by the native observation and cannot satisfy the
contract. The tool makes no claim to infer general dynamic-provider cardinality.

Every strategy runs on the same compiled candidate within a layout. Gold
controls use the unmodified developer test code. Jsoup's authored candidate
retains the old assertion in the repaired test. Codec's authored candidate
substitutes the standard encoder in the URL-safe round-trip test. The exact
source, annotations, fixture scopes and role expectations are frozen before
Azure execution. Unannotated helper methods are exclusion controls.

Seven layouts

Original source, canonical preceding annotations, inline annotations,
multiline annotation arguments, fully qualified annotation names, a block
comment between annotation and declaration, and a twenty-blank-line gap.
The variants are dependent authored perturbations. Codec was already inspected
before this study. Its transfer role is source-exposed, not blind validation.
The study records all compilation, equivalence and runtime failures.

Results

Inspect REPORT.json and the per-variant native.stdout/native.stderr records,
native command receipts, inventory, generated source, and class-loading logs.
Do not infer scientific success from the driver exit alone. Require completed,
review every qualification/error field, and check all complete gold/candidate
controls. The finite layout matrix supports an existence and repair result,
not an estimate of defect prevalence in all projects, languages or agents.

Sources and preparation

Jsoup sources are from developer commit
001752f1a0b73ae17668dc9fd4c5942424a6c1e2 in jhy/jsoup. Its MIT license is
retained in cases/jsoup/LICENSE. Commons Codec sources are from
d594dd25868063be2ea5a7744123393d66cad479 in apache/commons-codec, with Apache
license and notices retained in cases/codec. Java sources and pom files come
from the research's retained source package. Unrelated test resources are
omitted, including upstream local TLS fixture keys. The selected test methods
do not consume those resources. Candidate files carry modification notices.

The TEBench predicate is downloaded from pinned revision
5f607183bd9f29b6c740eae76b0489dd0c7556d5 and checked against its complete-source
and selected-function hashes. It is not redistributed in this public-prepared
kit. Dependency URLs, lengths and SHA256 values are in DEPENDENCIES.json.
Pinned upstream licenses apply to their respective code and artifacts.

The kit is prepared locally for review. Preparing it does not publish it,
attach a Kaggle resource or submit a paper. It contains no cloud controllers,
cloud account IDs, credentials, private input archives or provider grants.

Saved native evidence

The evidence directory contains sanitized native result archives for both
primary runs. Original native transcript bytes, command receipts, class-loading
logs and classfile-map records are preserved. Generated Java copies and the
outer cloud-wrapper command are omitted. Source variants regenerate from this
kit. Original/private and public/sanitized archive digests are separately
labeled in SAVED_LAYOUT_PROJECTION.json. No provider lifecycle record is public.

Verify the saved native evidence with this standard-library CPU command.

  python3 summarize.py --jsoup evidence/jsoup_result.tar.gz --codec evidence/codec_result.tar.gz --output summary.json

This analysis does not execute Java. It rechecks the saved native transcripts
and count contracts before producing the finite matrix. The cases, layouts
and candidate roles remain dependent, and all incorrect candidates are authored.
