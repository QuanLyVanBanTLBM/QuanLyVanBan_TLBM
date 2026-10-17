import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
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

const localDatabaseEnvironment = {
  DJANGO_SECRET_KEY: "qlvb-local-only-not-for-production",
  DJANGO_DEBUG: "true",
  DJANGO_ALLOWED_HOSTS: "127.0.0.1,localhost",
  DB_ENGINE: "postgresql",
  DB_NAME: "qlvb_dev",
  DB_USER: "qlvb_dev",
  DB_PASSWORD: "qlvb_local_only",
  DB_HOST: "127.0.0.1",
  DB_PORT: "55432",
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
  await runChecked("docker", ["compose", ...args]);
}

async function ensurePythonEnvironment() {
  if (!existsSync(python)) {
    const launcher = process.platform === "win32" ? "py" : "python3.12";
    const launcherArgs = process.platform === "win32"
      ? ["-3.12", "-m", "venv", venvDir]
      : ["-m", "venv", venvDir];

    console.log("Đang tạo môi trường Python 3.12+ trong backend/.venv...");
    try {
      await runChecked(launcher, launcherArgs);
    } catch {
      throw new Error("Không thể tạo backend/.venv. Cài Python 3.12+ rồi chạy lại lệnh.");
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
    await runChecked(python, ["-m", "pip", "install", "-r", requirementsFile], { cwd: backendDir });
    writeFileSync(dependencyMarker, `${requirementsHash}\n`, "utf8");
  }
}

function djangoEnvironment() {
  return { ...process.env, ...localDatabaseEnvironment };
}

async function django(...args) {
  await runChecked(python, ["manage.py", ...args], {
    cwd: backendDir,
    env: djangoEnvironment(),
  });
}

async function requireLocalDatabase() {
  const code = await run("docker", [
    "compose", "exec", "-T", "db", "pg_isready", "-U", "qlvb_dev", "-d", "qlvb_dev",
  ]);
  if (code !== 0) {
    throw new Error("PostgreSQL local chưa sẵn sàng. Mở Docker Desktop rồi chạy `pnpm db:start`.");
  }
}

function requireDockerEngine() {
  const result = spawnSync("docker", ["info", "--format", "{{.ServerVersion}}"], {
    stdio: "ignore",
  });
  if (result.error || result.status !== 0) {
    throw new Error("Docker Desktop/Engine chưa chạy. Mở Docker Desktop, chờ Docker sẵn sàng rồi chạy lại `pnpm runserver`.");
  }
}

function printLocalUrls() {
  console.log("\nPostgreSQL local: 127.0.0.1:55432 / database qlvb_dev");
  console.log("pgAdmin local:    http://127.0.0.1:5050");
  console.log("pgAdmin login:    admin@qlvb.local / qlvb_pgadmin_local_only");
}

async function setupDatabase() {
  await dockerCompose(["up", "--detach", "--wait", "db", "pgadmin"]);
  await ensurePythonEnvironment();
  await django("migrate", "--noinput");
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
  await runChecked("docker", [
    "compose", "exec", "-T", "db", "psql", "-U", "qlvb_dev", "-d", "postgres",
    "-v", "ON_ERROR_STOP=1",
    "-c", "DROP DATABASE IF EXISTS qlvb_dev WITH (FORCE)",
    "-c", "CREATE DATABASE qlvb_dev OWNER qlvb_dev",
  ]);
  await ensurePythonEnvironment();
  await django("migrate", "--noinput");
  console.log("Đã tạo lại DB local rỗng và áp dụng các migration Django.");
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
    await django("migrate", "--noinput");
  },
  "db-migrations": async () => {
    await ensurePythonEnvironment();
    await requireLocalDatabase();
    await django("showmigrations", "--plan");
  },
  "db-reset": resetDatabase,
  "db-stop": async () => dockerCompose(["stop", "db", "pgadmin"]),
  runserver: async () => {
    requireDockerEngine();
    await requireLocalDatabase();
    await ensurePythonEnvironment();
    await django("runserver", "127.0.0.1:8000");
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
