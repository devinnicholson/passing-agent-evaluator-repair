import java.io.File;
import org.jacoco.cli.internal.core.tools.ExecFileLoader;
import org.jacoco.cli.internal.core.data.ExecutionData;

/** Exact JaCoCo execution-data view. Session timestamps are not coverage. */
public final class ProbeDump {
    public static void main(String[] args) throws Exception {
        ExecFileLoader loader = new ExecFileLoader();
        loader.load(new File(args[0]));
        int matches = 0;
        for (ExecutionData data : loader.getExecutionDataStore().getContents()) {
            if (!data.getName().equals(args[1])) continue;
            matches++;
            StringBuilder bits = new StringBuilder();
            for (boolean value : data.getProbes()) bits.append(value ? '1' : '0');
            System.out.println(data.getName() + "\t" + Long.toHexString(data.getId()) + "\t" + bits.toString());
        }
        if (matches != 1) throw new IllegalStateException("expected exactly one production class record");
    }
}
