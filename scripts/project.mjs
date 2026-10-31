import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawn, spawnSync } from "node:child_process";
import { createInterface } from "node:readline/promises";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const backendDir = path.join(projectRoot, "backend");
const venvDir = path.join(backendDir, ".venv");
const requirementsFile = path.join(backendDir, "requirements.txt");
const dependencyMarker = path.join(venvDir, ".requirements.sha256");
const python = process.platform === "win32"
  ? path.join(venvDir, "Scripts", "python.exe")
  : path.join(venvDir, "bin", "python");

const dbPort = process.env.QLVB_DB_PORT?.trim() || "55432";
const pgadminPort = process.env.QLVB_PGADMIN_PORT?.trim() || "5050";
for (const [name, value] of [["QLVB_DB_PORT", dbPort], ["QLVB_PGADMIN_PORT", pgadminPort]]) {
  if (!/^\d+$/.test(value)) {
    console.error(`${name} phải là số cổng (đang là "${value}").`);
    process.exit(1);
  }
}

// DB local do compose.yaml dựng; nguồn duy nhất cho thông tin kết nối khi chạy qua pnpm.
const localDatabaseEnvironment = {
  DJANGO_SECRET_KEY: "qlvb-local-only-not-for-production",
  DJANGO_DEBUG: "true",
  DJANGO_ALLOWED_HOSTS: "127.0.0.1,localhost",
  DB_ENGINE: "postgresql",
  DB_NAME: "qlvb_dev",
  DB_USER: "qlvb_dev",
  DB_PASSWORD: "qlvb_local_only",
  DB_HOST: "127.0.0.1",
  DB_PORT: dbPort,
  PYTHONUTF8: "1",
};

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: options.cwd ?? projectRoot,
      env: options.env ?? process.env,
      stdio: "inherit",
      shell: false,
    });

    child.once("error", reject);
    child.once("exit", (code) => resolve(code ?? 1));
  });
}

async function runChecked(command, args, options = {}) {
  const code = await run(command, args, options);
  if (code !== 0) {
    throw new Error(`Lệnh thất bại với mã ${code}: ${command} ${args.join(" ")}`);
  }
}

async function dockerCompose(args) {
  requireDockerEngine();
  await runChecked("docker", ["compose", ...args], {
    env: { ...process.env, QLVB_DB_PORT: dbPort, QLVB_PGADMIN_PORT: pgadminPort },
  });
}

async function ensurePythonEnvironment() {
  if (!existsSync(python)) {
    const launcher = process.platform === "win32" ? "py" : "python3";
    const launcherArgs = process.platform === "win32"
      ? ["-3", "-m", "venv", venvDir]
      : ["-m", "venv", venvDir];

    console.log("Đang tạo môi trường Python 3.12+ trong backend/.venv...");
    try {
      await runChecked(launcher, launcherArgs);
    } catch {
      throw new Error("Không thể tạo backend/.venv. Cài Python 3.12+ (Windows: có lệnh `py`; Linux/macOS: `python3`) rồi chạy lại lệnh.");
    }
  }

  const version = spawnSync(python, ["-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"], {
    encoding: "utf8",
  });
  if (version.status !== 0) {
    throw new Error("Không đọc được phiên bản Python trong backend/.venv.");
  }

  const [major, minor] = version.stdout.trim().split(".").map(Number);
  if (major < 3 || (major === 3 && minor < 12)) {
    throw new Error(`backend/.venv đang dùng Python ${version.stdout.trim()}; dự án yêu cầu Python 3.12 trở lên.`);
  }

  const requirementsHash = createHash("sha256").update(readFileSync(requirementsFile)).digest("hex");
  const installedHash = existsSync(dependencyMarker) ? readFileSync(dependencyMarker, "utf8").trim() : "";
  if (requirementsHash !== installedHash) {
    console.log("Đang cài/cập nhật thư viện backend theo backend/requirements.txt...");
    await runChecked(python, ["-m", "pip", "install", "-r", requirementsFile], {
      cwd: backendDir,
      env: { ...process.env, PYTHONUTF8: "1" },
    });
    writeFileSync(dependencyMarker, `${requirementsHash}\n`, "utf8");
  }
}

function djangoEnvironment() {
  return { ...process.env, ...localDatabaseEnvironment, PYTHONUTF8: "1", QLVB_DB_PORT: dbPort, QLVB_PGADMIN_PORT: pgadminPort };
}

async function django(...args) {
  await runChecked(python, ["manage.py", ...args], {
    cwd: backendDir,
    env: djangoEnvironment(),
  });
}

async function requireLocalDatabase() {
  requireDockerEngine();
  const code = await run("docker", [
    "compose", "exec", "-T", "db", "pg_isready", "-U", "qlvb_dev", "-d", "qlvb_dev",
  ], { env: { ...process.env, QLVB_DB_PORT: dbPort, QLVB_PGADMIN_PORT: pgadminPort } });
  if (code !== 0) {
    throw new Error("PostgreSQL local chưa sẵn sàng. Mở Docker Desktop rồi chạy `pnpm db:start`.");
  }
}

function requireDockerEngine() {
  const result = spawnSync("docker", ["info", "--format", "{{.ServerVersion}}"], {
    stdio: "ignore",
  });
  if (result.error) {
    throw new Error("Không tìm thấy `docker` trong PATH. Cài Docker Desktop rồi chạy lại lệnh.");
  }
  if (result.status !== 0) {
    throw new Error("Docker Desktop/Engine chưa chạy. Mở Docker Desktop, chờ Docker sẵn sàng rồi chạy lại lệnh.");
  }
}

function printLocalUrls() {
  console.log(`\nPostgreSQL local: 127.0.0.1:${dbPort} / database qlvb_dev`);
  console.log(`pgAdmin local:    http://127.0.0.1:${pgadminPort}`);
  console.log("pgAdmin login:    admin@qlvb.local / qlvb_pgadmin_local_only");
}

async function buildDatabase(...args) {
  if (args.includes("--seed") && !process.env.ADMIN_PASSWORD?.trim()) {
    throw new Error("Thiếu ADMIN_PASSWORD; database chưa bị thay đổi.");
  }
  if (args.includes("--demo-data") && !process.env.DEMO_PASSWORD?.trim()) {
    throw new Error("Thiếu DEMO_PASSWORD cho --demo-data; database chưa bị thay đổi.");
  }
  await runChecked(python, [path.join(projectRoot, "scripts", "build_db.py"), ...args], {
    env: djangoEnvironment(),
  });
}

async function setupDatabase() {
  requireDockerEngine();
  await dockerCompose(["up", "--detach", "--wait", "db", "pgadmin"]);
  await ensurePythonEnvironment();
  await buildDatabase("--if-empty", "--seed");
  printLocalUrls();
}

async function resetDatabase() {
  const terminal = createInterface({ input: process.stdin, output: process.stdout });
  let answer;
  try {
    answer = await terminal.question("Thao tác này xóa dữ liệu trong DB local qlvb_dev. Gõ RESET để tiếp tục: ");
  } finally {
    terminal.close();
  }

  if (answer !== "RESET") {
    console.log("Đã hủy; database không bị thay đổi.");
    return;
  }

  await requireLocalDatabase();
  await ensurePythonEnvironment();
  await buildDatabase("--force", "--seed");
  console.log("Đã dựng lại DB local từ release_DDL.sql và đồng bộ migration Django.");
}

const deployPaths = ["backend", "scripts", "docs/common/database", ".github/scripts/compare_schema_ddl.py"];

function requireCommand(command, args, hint) {
  const result = spawnSync(command, args, { stdio: "ignore", shell: false });
  if (result.error) {
    throw new Error(`Không tìm thấy \`${command}\` trong PATH. ${hint}`);
  }
}

function git(args, options = {}) {
  const result = spawnSync("git", args, { cwd: projectRoot, shell: false, ...options });
  if (result.error || result.status !== 0) {
    const detail = result.stderr ? `
${result.stderr.toString().trim()}` : "";
    throw new Error(`Lệnh git thất bại: git ${args.join(" ")}${detail}`);
  }
  return result.stdout;
}

async function deployStaging(...args) {
  if (args.includes("--help")) {
    console.log([
      "Dùng: pnpm deploy:staging [--yes] [--reset-db]",
      "Deploy origin/staging lên host staging (DB_MODE=sync mặc định) bằng deploy/deploy.sh.",
      "--reset-db chọn DB_MODE=rebuild và luôn yêu cầu gõ RESET; --yes không bỏ xác nhận này.",
      "Biến môi trường: QLVB_DEPLOY_HOST (bắt buộc; alias trong ~/.ssh/config hoặc user@host),",
      "QLVB_DEPLOY_PORT (tùy chọn; đặt thì truyền -p/-P, không đặt thì dùng cấu hình ssh).",
      "--yes chỉ bỏ bước gõ DEPLOY xác nhận.",
    ].join(os.EOL));
    return;
  }

  const allowedArgs = new Set(["--yes", "--reset-db"]);
  const unknownArgs = args.filter((arg) => !allowedArgs.has(arg));
  if (unknownArgs.length) {
    throw new Error(`Tham số deploy không hợp lệ: ${unknownArgs.join(", ")}.`);
  }
  const resetDatabase = args.includes("--reset-db");

  const target = process.env.QLVB_DEPLOY_HOST?.trim();
  if (!target) {
    throw new Error("Thiếu QLVB_DEPLOY_HOST. Thêm alias vào ~/.ssh/config (Host qlvb-staging / HostName / User / Port) "
      + "rồi đặt QLVB_DEPLOY_HOST=qlvb-staging, hoặc đặt QLVB_DEPLOY_HOST=user@host kèm QLVB_DEPLOY_PORT.");
  }
  if (target.startsWith("-")) {
    throw new Error("QLVB_DEPLOY_HOST không hợp lệ.");
  }
  const port = process.env.QLVB_DEPLOY_PORT?.trim();
  if (port && !/^\d+$/.test(port)) {
    throw new Error("QLVB_DEPLOY_PORT phải là số.");
  }

  requireCommand("git", ["--version"], "Cài Git rồi chạy lại.");
  requireCommand("ssh", ["-V"], "Bật OpenSSH Client (Windows: Settings > Optional features) rồi chạy lại.");
  requireCommand("scp", [], "Bật OpenSSH Client (Windows: Settings > Optional features) rồi chạy lại.");

  console.log("Đang fetch origin/staging (không thay đổi working tree)...");
  git(["fetch", "origin", "staging"], { stdio: "inherit" });
  const commit = git(["rev-parse", "--verify", "origin/staging^{commit}"]).toString().trim();
  const sha7 = git(["rev-parse", "--short=7", commit]).toString().trim();
  const subject = git(["log", "-1", "--format=%s", commit]).toString().trim();

  const tmpDir = mkdtempSync(path.join(os.tmpdir(), "qlvb-deploy-"));
  try {
    const tarball = `qlvb-${sha7}.tar.gz`;
    git(["-c", "core.autocrlf=false", "archive", "--format=tar.gz", "-o", path.join(tmpDir, tarball), commit, ...deployPaths]);
    writeFileSync(path.join(tmpDir, "deploy.sh"), git(["show", `${commit}:deploy/deploy.sh`], { maxBuffer: 16 * 1024 * 1024 }));
    writeFileSync(path.join(tmpDir, "qlvb-frontend.nginx"), git(["show", `${commit}:deploy/nginx/qlvb-frontend.conf`]));

    console.log("");
    console.log(`Commit:  ${sha7} ${subject}`);
    console.log(`Host:    ${target}${port ? `:${port}` : ""}`);
    const dbMode = resetDatabase ? "rebuild" : "sync";
    console.log(`DB_MODE: ${dbMode}`);
    if (resetDatabase) {
      console.log("Cảnh báo: DB staging sẽ bị xóa và dựng lại từ release_DDL.sql.");
      const terminal = createInterface({ input: process.stdin, output: process.stdout });
      let answer;
      try {
        answer = await terminal.question("Gõ RESET để xác nhận xóa dữ liệu staging: ");
      } finally {
        terminal.close();
      }
      if (answer !== "RESET") {
        console.log("Đã hủy; không có gì được tải lên host.");
        process.exitCode = 1;
        return;
      }
    }

    if (!args.includes("--yes")) {
      const terminal = createInterface({ input: process.stdin, output: process.stdout });
      let answer;
      try {
        answer = await terminal.question("Gõ DEPLOY để tiếp tục: ");
      } finally {
        terminal.close();
      }
      if (answer !== "DEPLOY") {
        console.log("Đã hủy; không có gì được tải lên host.");
        process.exitCode = 1;
        return;
      }
    }

    const sshOptions = port ? ["-p", port] : [];
    const scpOptions = port ? ["-P", port] : [];
    const options = { cwd: tmpDir };

    await runChecked("ssh", [...sshOptions, target, 'mkdir -p "$HOME/deploy"'], options);
    await runChecked("scp", [...scpOptions, tarball, "deploy.sh", "qlvb-frontend.nginx", `${target}:deploy/`], options);
    const code = await run("ssh", [...sshOptions, target, `DB_MODE=${dbMode} bash deploy/deploy.sh ${sha7}`], options);
    if (code !== 0) {
      process.exitCode = code;
      console.error("");
      console.error(`deploy.sh kết thúc với mã ${code}. Xem log /srv/qlvb/deploy.log trên host.`);
      return;
    }
    console.log("");
    console.log(`Đã deploy ${sha7} lên ${target}.`);
  } finally {
    rmSync(tmpDir, { recursive: true, force: true });
  }
}

const actions = {
  "db-setup": setupDatabase,
  "db-start": async () => {
    await dockerCompose(["up", "--detach", "--wait", "db", "pgadmin"]);
    printLocalUrls();
  },
  "db-status": async () => {
    await dockerCompose(["ps", "db", "pgadmin"]);
    printLocalUrls();
    console.log("Nếu container chưa ở trạng thái Up/healthy, chạy `pnpm db:start`.");
  },
  "db-migrate": async () => {
    await ensurePythonEnvironment();
    await requireLocalDatabase();
    await buildDatabase("--sync");
  },
  "db-adopt": async () => {
    if (process.argv.slice(3).some((argument) => argument === "--help" || argument === "-h")) {
      console.log("Usage: pnpm db:adopt");
      console.log("Verifies the supported build_db:v2 schema and migration history before upgrading its marker.");
      return;
    }
    await ensurePythonEnvironment();
    await requireLocalDatabase();
    await buildDatabase("--adopt");
  },
  "db-migrations": async () => {
    await ensurePythonEnvironment();
    await requireLocalDatabase();
    await django("showmigrations", "--plan");
  },
  "db-reset": resetDatabase,
  "db-stop": async () => dockerCompose(["stop", "db", "pgadmin"]),
  "deploy-staging": () => deployStaging(...process.argv.slice(3)),
  runserver: async () => {
    await requireLocalDatabase();
    await ensurePythonEnvironment();
    await django("runserver", "127.0.0.1:8000");
  },
  manage: async () => {
    await requireLocalDatabase();
    await ensurePythonEnvironment();
    await django(...process.argv.slice(3));
  },
  "test-backend": async () => {
    await requireLocalDatabase();
    await ensurePythonEnvironment();
    await django("test", ...process.argv.slice(3));
  },
};

try {
  const action = actions[process.argv[2]];
  if (!action) {
    throw new Error("Lệnh không hợp lệ. Xem danh sách lệnh trong README.md ở thư mục gốc.");
  }
  await action();
} catch (error) {
  console.error(`\n${error.message}`);
  process.exitCode = 1;
}
