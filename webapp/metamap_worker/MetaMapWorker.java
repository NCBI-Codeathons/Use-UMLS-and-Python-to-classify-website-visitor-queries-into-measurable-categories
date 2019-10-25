import java.io.*;
import java.util.List;
import java.util.ArrayList;
import gov.nih.nlm.nls.skr.*;

import java.nio.file.*;
import static java.nio.file.StandardWatchEventKinds.*;
import static java.nio.file.LinkOption.*;
import java.nio.file.attribute.*;
import java.io.*;
import java.util.*;

public class MetaMapWorker {
  private void processMetaMapJob(Path inputPathname, Path outputPathname) {
    // NOTE: You MUST specify an email address because it is used for
    // logging purposes.
    String emailAddress = System.getenv("UMLS_EMAIL");
    String username = System.getenv("UMLS_USERNAME");
    String password = System.getenv("UMLS_PASSWORD");
    String batchCommand = "metamap -V USAbase -N -E -A+";
    String batchNotes = "Classification of website visitor queries using UMLS";
    boolean silentEmail = false;
    boolean silentOnErrors = false;
    boolean singleLineDelimitedInput = false;
    boolean singleLineDelimitedInputWithId = false;
    int priority = -1;

    List<String> options = new ArrayList<String>();

    // Instantiate the object for Generic Batch
    GenericObject myGenericObj = new GenericObject(username, password);
    myGenericObj.setField("Email_Address", emailAddress);

    myGenericObj.setField("Batch_Command", batchCommand);
    if (batchNotes != null) {
      myGenericObj.setField("BatchNotes", batchNotes);
    }
    myGenericObj.setField("SilentEmail", silentEmail);
    if (silentOnErrors) {
      myGenericObj.setField("ESilent", silentOnErrors);
    }
    if (singleLineDelimitedInput) {
      myGenericObj.setField("SingLine", singleLineDelimitedInput);
    }
    if (singleLineDelimitedInputWithId) {
      myGenericObj.setField("SingLinePMID", singleLineDelimitedInputWithId);
    }
    if (priority > 0) {
      myGenericObj.setField("RPriority", Integer.toString(priority));
    }

    myGenericObj.setFileField("UpLoad_File", inputPathname.toString());

    try {
      // Submit the job request
      String results = myGenericObj.handleSubmission();

      try (FileWriter writer = new FileWriter(outputPathname.toFile())) {
        writer.write(results);
      }
    } catch (Exception ex) {
      try {
        ex.printStackTrace();

        try (PrintWriter writer = new PrintWriter(outputPathname.toFile())) {
          String error = "ERROR MESSAGE: ";
          error += "An error has occurred while processing your request";
          error += "; please review stderr log.";
          writer.println(error);
        }
      } catch (Exception ex2) {
        ex2.printStackTrace();
      }
    }
  }

  private final WatchService watcher;
  private final Map<WatchKey, Path> keys;
  private boolean trace = false;

  @SuppressWarnings("unchecked")
  static <T> WatchEvent<T> cast(WatchEvent<?> event) {
    return (WatchEvent<T>) event;
  }

  /**
   * Register the given directory with the WatchService
   */
  private void register(Path dir) throws IOException {
    WatchKey key = dir.register(watcher, ENTRY_CREATE);
    if (trace) {
      Path prev = keys.get(key);
      if (prev == null) {
        System.out.format("register: %s\n", dir);
      } else if (!dir.equals(prev)) {
        System.out.format("update: %s -> %s\n", prev, dir);
      }
    }
    keys.put(key, dir);
  }

  /**
   * Creates a WatchService and registers the given directory
   */
  MetaMapWorker(Path inputDir) throws IOException {
    this.watcher = FileSystems.getDefault().newWatchService();
    this.keys = new HashMap<WatchKey, Path>();

    register(inputDir);

    // enable trace after initial registration
    this.trace = true;
  }

  /**
   * Process all events for keys queued to the watcher
   */
  void processJobs(Path outputDir) {
    for (;;) {
      // wait for key to be signalled
      WatchKey key;
      try {
        key = watcher.take();
      } catch (InterruptedException x) {
        return;
      }

      Path dir = keys.get(key);
      if (dir == null) {
        System.err.println("WatchKey not recognized!!");
        continue;
      }

      for (WatchEvent<?> event : key.pollEvents()) {
        WatchEvent.Kind kind = event.kind();

        if (kind == OVERFLOW) {
          continue;
        }

        // Context for directory entry event is the file name of entry
        WatchEvent<Path> ev = cast(event);
        Path name = ev.context();

        if (!name.toString().endsWith(".tmp")) {
          System.out.format("Processing %s...\n", name);
          processMetaMapJob(dir.resolve(name), outputDir.resolve(name));
        }
      }

      // reset key and remove from set if directory no longer accessible
      boolean valid = key.reset();
      if (!valid) {
        keys.remove(key);

        // all directories are inaccessible
        if (keys.isEmpty()) {
          break;
        }
      }
    }
  }

  public static void main(String[] args) throws IOException {
    Path inputDir = Paths.get(System.getenv("JOB_INPUT_DIR"));
    Path outputDir = Paths.get(System.getenv("JOB_OUTPUT_DIR"));

    Files.createDirectories(inputDir);
    Files.createDirectories(outputDir);

    // register input directory and process its events
    new MetaMapWorker(inputDir).processJobs(outputDir);
  }
}
