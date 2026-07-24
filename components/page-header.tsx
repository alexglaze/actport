export function PageHeader({
  title,
  intro,
}: {
  title: string;
  intro?: string;
}) {
  return (
    <div className="mx-auto max-w-5xl px-6 pt-16 pb-10 sm:pt-24">
      <h1 className="font-display text-4xl tracking-tight sm:text-5xl">{title}</h1>
      {intro ? (
        <p className="text-muted mt-4 max-w-xl text-lg leading-relaxed">{intro}</p>
      ) : null}
    </div>
  );
}
