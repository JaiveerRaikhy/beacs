import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8">
      <h1 className="text-2xl font-semibold text-gray-900 mb-4">Beacon</h1>
      <p className="text-gray-600 mb-6">Bilateral mentor-mentee matching</p>
      <div className="flex gap-4">
        <Link
          href="/login"
          className="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
        >
          Log in
        </Link>
        <Link
          href="/signup"
          className="px-4 py-2 bg-gray-900 text-white rounded hover:bg-gray-800"
        >
          Sign up
        </Link>
      </div>
    </main>
  );
}
